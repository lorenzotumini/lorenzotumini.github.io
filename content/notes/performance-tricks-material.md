# Performance tricks: selected material

This is a research sheet for a future article about practical performance work
in C. The selection favors techniques that generalize beyond one interpreter,
are easy to demonstrate with a small independent example, and are useful
knowledge for a programmer who already understands ordinary data structures and
big-O notation.

The article should explain mechanisms and tradeoffs, not present a collection
of benchmark results. The examples below can be implemented as small standalone
C programs or pseudocode exercises.

## Possible thesis

The most interesting optimizations often remove bookkeeping around the useful
work: an allocation, an ownership transition, a repeated lookup, a temporary
copy, or the creation of a short-lived execution record. The recurring design
is a cheap common case with an explicit fallback for values or situations that
do not fit it.

## Selected techniques

### 1. Store common values inside the value representation

Pointer tagging stores a small value in a word that would otherwise be a
pointer. A runtime can reserve one or more tag bits and distinguish an encoded
integer, boolean, enum, or special singleton from a real object pointer.

General example:

```c
typedef uintptr_t value;

enum { TAG_INT = 1 };

static inline value int_value(intptr_t n) {
    return ((uintptr_t)n << 1) | TAG_INT;
}

static inline intptr_t value_int(value v) {
    return ((intptr_t)v) >> 1;
}
```

This illustrative example needs production safeguards: the representable range must be
checked, conversions should use `uintptr_t`/`intptr_t`, and the implementation
must document its alignment and platform assumptions. A real object system
also needs one consistent definition of equality, hashing, tracing,
refcounting, and API conversion for both immediate and heap representations.

Interesting variations include low-bit pointer tags, tagged unions stored in a
machine word, and NaN-boxing in runtimes that use floating-point values. The
important idea is not “make integers faster”; it is that a ubiquitous small
object can disappear from the allocation and pointer-chasing paths.

Questions for the article:

- Which bits are genuinely available on the target architecture?
- What happens at the boundary of the immediate range?
- How does the fallback representation preserve exactly the same semantics?
- Is the saved allocation cost worth the extra branches and portability work?

### 2. Use inline storage for the overwhelmingly common small case

Small-buffer optimization (SBO) puts a short payload directly in its owning
object and allocates only when the payload outgrows that space. It applies to
strings, vectors, arrays of callback arguments, path names, error messages,
temporary buffers, and parser tokens.

General layout:

```c
struct small_buffer {
    size_t length;
    size_t capacity;
    char *data;
    char inline_data[24];
};
```

The representation needs a reliable way to distinguish inline and heap storage,
and the move/copy/destructor operations must handle both cases. Inline space
also enlarges every instance, including objects whose payload is always large
or always empty. Capacity should therefore come from a measured distribution,
not from a desire to avoid every allocation.

A useful refinement is delayed promotion: keep the first few elements inline,
and allocate only when the object crosses the inline threshold. Another is a
bounded reserve after the threshold, which avoids repeated growth without
preallocating a large array for sparse results.

Related but different: inline storage keeps data near its owner; an inline
cache keeps the result of a repeated computation near the operation that uses
it.

### 3. Match allocation strategy to object lifetime

General-purpose `malloc` is flexible, but it is not the only useful allocation
policy. Choose a policy from the lifetime shape of the objects:

- **Arena / region allocation:** allocate many objects from a bump pointer and
  release the region as a group. Good for request handling, compiler passes,
  parsing phases, and temporary graphs.
- **Scratch arena:** use strict LIFO storage for temporary buffers or snapshots;
  rewind to a saved mark when the operation ends. Nested operations can link
  another block, while a bounded spare cache prevents an unusual peak from
  becoming permanent memory.
- **Slab allocation:** allocate fixed-size records in pages or slabs. This
  reduces allocator calls, improves locality, and makes free-list management
  cheap for node-like objects.
- **Object pools:** recycle objects when construction/destruction is frequent
  and the object size is stable. A per-thread or per-context pool can avoid a
  lock on the ordinary path.

The less obvious part is the bound. Reusing memory is not free if a short burst
leaves the process holding its entire historical high-water mark. Retain only
the spare capacity justified by the expected workload, and release excess
blocks after an exceptional peak.

Failure modes worth showing:

- using an arena when objects escape the intended phase;
- returning a pooled object to the wrong owner or thread;
- adding synchronization to a global pool and losing the benefit;
- retaining a large scratch arena forever after one pathological input.

### 4. Coalesce related allocations with a flexible array member

When a record owns a variable number of tightly coupled values, a single
variable-sized allocation can replace a header allocation plus one or more
auxiliary allocations.

```c
struct task {
    void (*function)(void);
    size_t argument_count;
    void *arguments[];
};

struct task *task_new(size_t count) {
    if (count > (SIZE_MAX - sizeof(struct task)) / sizeof(void *))
        return NULL;
    return malloc(sizeof(struct task) + count * sizeof(void *));
}
```

This improves locality and reduces allocator metadata, pointer indirections,
and teardown steps. It is particularly useful for queued messages, AST nodes
with a variable child count, network packets, and callback records whose size
is known when they are created.

The design must include overflow checks, alignment, ownership rules for the
tail elements, and a clear answer to whether the record may be resized. The
technique is not a universal replacement for a general vector: it is best when
the count is fixed at construction and the fields share a lifetime.

### 5. Cache resolution, not just data

An inline cache remembers the answer to a costly operation at the place where
the operation repeats. Common applications include dynamic method dispatch,
symbol or configuration lookup, schema resolution, and property access.

A useful cache entry has four parts:

1. a key or compact description of the call site;
2. a cheap hit check, often identity or a type/version value;
3. the resolved target or other expensive result;
4. a way to invalidate the entry when the world changes.

For mutable systems, a generation counter is often simpler than walking every
cache entry on every update. A lookup records the generation at which it was
validated; a definition change increments the generation; the next use falls
back to the slow path and refreshes the entry.

The cache can be direct-mapped for a tiny fast table, set-associative when
several hot keys collide, or polymorphic when one call site commonly sees a
small number of types. Pointer identity alone is dangerous when objects can be
freed and their addresses reused. Retaining a key may fix that correctness
problem, but it changes memory lifetime and must be part of the design.

The interesting lesson is that caching requires a mutation model. A cache with
no invalidation story is not an optimization; it is a latent correctness bug.

### 6. Preserve uniqueness to avoid accidental copies

Reference counting and copy-on-write make sharing convenient, but a single
extra reference can turn an update into a full copy. This is easy to miss when
an API returns a borrowed-looking handle, a closure captures an accumulator,
or an error path retains a temporary snapshot “just in case.”

General example:

```c
/* Fast only when buffer->refcount == 1. */
void append_byte(buffer *buffer, unsigned char byte);

buffer *next = buffer_clone_if_shared(current);
append_byte(next, byte);
```

The optimization is not merely “use mutable state.” It is to make ownership
flow explicit so that the common update remains unique. Pass an accumulator
through a loop rather than repeatedly fetching it from a shared environment;
retain snapshots only at genuine recovery or isolation boundaries; and make
state-threading operations transfer the current value instead of preserving an
obsolete copy.

This can change scaling dramatically: repeated accidental copies can turn an
apparently linear builder into quadratic work. The right diagnosis is to count
copies and retained references, not only to inspect the surface algorithm.

### 7. Reuse a hot state machine instead of recreating its records

Many interpreters, parsers, schedulers, and protocol handlers repeatedly create
small execution records whose only changing fields are a counter, cursor, or
program position. If the state is safe to reuse, one record can replace a long
sequence of short-lived records.

General example: a repeat operation can keep one frame containing the body,
program counter, and remaining count. On completion of the body it decrements
the count and resets the program counter. It does not create a new frame and
continuation for every iteration.

This is a targeted form of specialization:

- guard it to a shape whose semantics are known, such as a capture-free body;
- store the new state in existing padding or reserved capacity when possible;
- keep rare completion, tracing, debugging, and error paths out of the hot
  loop;
- fall back to the general implementation when captures, hooks, or unusual
  values make reuse unsafe.

The broader C lesson is to specialize a repeated state transition while
preserving the generic state machine. This can remove a large amount of
bookkeeping without requiring a complete bytecode, JIT, or scheduler rewrite.

### 8. Use a sidecar only when it removes work

An auxiliary representation can be attractive: cached opcodes beside source
objects, a lookup table beside a parsed structure, or metadata beside a packed
array. But a sidecar that leaves the old representation in the hot path may
duplicate fetches and branches instead of replacing them.

Before adding one, identify exactly which old operation disappears. If the
original object still has to be fetched for values, source locations, tracing,
and debugging, a second instruction stream may cost more than it saves. A
successful sidecar needs a clear ownership model, invalidation policy, and a
measured reduction in hot-path work.

This is a useful negative lesson because it guards against optimizing the
architecture diagram rather than the executed path.

## Measurement principles

Keep this section short in the article, but use it to evaluate every example:

- Change one mechanism at a time and compare on the same machine and build.
- Measure enough alternating runs to see variance; do not select the fastest
  result.
- Use profiles or counters to explain why the result changed.
- Measure allocation calls, requested bytes, cache misses, copies, or state
  transitions when those are the proposed mechanism.
- Test scaling at several input sizes.
- Keep correctness, sanitizer, and leak checks separate from the timed region.
- Include a control workload that should not use the specialization.
- Record negative results when the proposed representation adds work.

## Deliberately omitted

- Basic advice to prefer an asymptotically better algorithm. It is important,
  but too familiar for the intended article unless needed as context.
- A standalone section on geometric growth. It remains a supporting policy for
  buffers and arrays, but is not the distinctive main idea here.
- Runtime-specific recursion-controller and continuation layouts. They can be
  translated into the more general state-machine and lifetime sections.
- Language-specific control combinators, syntax, and benchmark names.
- Cross-language rankings. They distract from mechanisms and depend heavily on
  workload, compiler, runtime version, and machine.

## Candidate standalone examples

1. A tagged `value` that stores small integers without allocation.
2. A small string with inline bytes and a heap fallback.
3. A request arena with nested scratch marks and bounded spare blocks.
4. A flexible-array callback record with overflow-safe sizing.
5. A versioned inline cache for dynamic property lookup.
6. A reference-counted buffer that copies only when shared.
7. A reusable repeat frame replacing per-iteration execution records.
8. A deliberately rejected sidecar that duplicates an existing fetch.
