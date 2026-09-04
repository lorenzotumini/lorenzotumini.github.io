Title: What They Don't Teach You in College
Date: 2026-08-12
Slug: what-they-don't-teach-you-in-college
Status: draft
Category: Technical notes
Summary: An article about less-obvious performance techniques in C and systems programming.

Now that that I have clickbaited you into opening this article I have to
convince you it might be a good idea to keep reading. Let's say you know some 
programming languages, you understand complexity and data structures, and you have
a decent understanding of how memory works (in short, the typical CS student).
Then you believe that having a solid technical foundation wins over the alternative 
- even now that you are one prompt away from glory - because what will distinguish you
from all the other prompters is the quality of your ideas. Maybe you don't even care
about that, and you love programming for its sake, for the joy that you find in problem
solving. In any case, in this article you will find ideas, tips and tricks they don't
teach you in college.

Side note 1: the examples are in C but most of the ideas apply in general, and even if 
they don't, they were too cool to exclude.

Side note 2: this article is handcrafted by me, the dashes are handcrafted too. English is 
not my native language, be kind.

## Pointer tagging

Once you realize that you need a single bit for each flag, you can 
pack multiple of them in a field with some clever masking:

```c
#define FLAG1 (1 << 0) // 0b00000001
#define FLAG2 (1 << 1) // 0b00000010
#define FLAG3 (1 << 2) // 0b00000100

// sizeof(struct obj): 12
struct obj {
    char id[4];
    int val;
    int flags; // can fit up to 32 flags
} o;

o.flags = FLAG1 | FLAG2
```

But what if i told you that you can store flags without reserving space in the struct? 
The trick exploits pointer alignment: on a 64-bit architecture data is always aligned
to the size of a work, namely 8 bytes. this means that every address that points to a region 
allocated on the heap will always be a multiple of 8, thus ending with the bits 000.
This renders those ending bits useless for adressing purposes and usable to store additional
data.
 
```c
#define FLAG1 (1 << 0) // 0b00000001
#define FLAG2 (1 << 1) // 0b00000010
#define FLAG3 (1 << 2) // 0b00000100
#define MASK 0x0111

// sizeof(struct obj): 8
struct obj {
    char id[4];
    int val;
};

struct obj *o = malloc(sizeof(struct obj));
o |= FLAG1 | FLAG2;

// to get the address back you mask out the flags
struct obj *ptr = o & ~MASK
```

You can even push this further and use the entire pointer to store data.
Suppose your program needs an object that can assume different values (integer,
float, string), but you want a general abstract interface. The classic solution
is a tagged union that lets you reserve just enough space for the biggest field
in the union.

```c 
// sizeof(struct obj): 8
struct obj {
    int type;
    union {
        int i;
        float f;
        char str[4];
    };
};
```

## 2. Small-buffer optimization

> Draft prompt: introduce inline storage with a heap fallback using a short
> string or vector. Explain why avoiding an allocation is often more important
> than making the payload operation itself faster.

Discuss:

- inline capacity selection;
- move/copy/destructor rules for two representations;
- delayed promotion and bounded reserve;
- the cost of enlarging every object.

## 3. Allocate according to lifetime

> Draft prompt: compare a general allocator with an arena, scratch arena, slab,
> and per-thread/per-context pool. Use one small request or parser example.

Show the lifetime shapes that justify each policy, then show failure modes:
escaping objects, wrong-owner frees, contention, fragmentation, and retaining a
pathological high-water mark.

## 4. Coalesce related allocations

> Draft prompt: write a flexible-array-member record for a callback, message, or
> AST node. Contrast one allocation with a header plus separately allocated
> pointer array.

The example should include overflow-safe size calculation, ownership of tail
elements, alignment, and the reason resizing is deliberately unsupported.

## 5. Inline caches and versioned resolution

> Draft prompt: explain how a dynamic property or method lookup can remember its
> previous answer. Build the explanation around key, hit check, cached result,
> generation/version, and slow-path refresh.

Cover:

- direct-mapped versus set-associative caches;
- monomorphic and small polymorphic call sites;
- why pointer reuse makes identity-only caches unsafe;
- why invalidation is part of correctness, not maintenance detail.

## 6. Ownership is part of performance

> Draft prompt: show how reference counting and copy-on-write can make an
> apparently linear update copy the entire buffer. Contrast a shared update
> with a unique accumulator passed through a loop.

Include a small counter or trace of copies and explain that a retain in an
error, closure, or observer path can change the complexity of the success path.

## 7. Reuse a hot state machine

> Draft prompt: show a repeat operation that reuses one frame containing a
> cursor/count/program position instead of allocating a record for every
> iteration.

The example should demonstrate:

- a narrow guard for the reusable case;
- state stored in existing slack where possible;
- an out-of-line rare completion or slow path;
- fallback behavior when captures, tracing, debugging, or unusual values make
  reuse unsafe.

## 8. Do not add a sidecar that duplicates work

> Draft prompt: present a deliberately tempting auxiliary representation and
> ask what original fetch, branch, or conversion it actually removes. Explain
> why preserving the old hot path can make the new representation slower.

This section can be short and serve as the article’s negative result.

## 9. How to test a performance claim

- [ ] Change one mechanism at a time.
- [ ] Compare on the same machine, compiler, and build configuration.
- [ ] Alternate baseline and candidate runs; report medians and variance.
- [ ] Measure the mechanism itself: allocations, bytes, copies, misses, or
      state transitions.
- [ ] Test multiple input sizes and include a control workload.
- [ ] Use a profile or counter to explain the observed change.
- [ ] Keep correctness, sanitizer, and leak checks separate from timing.
- [ ] Record rejected ideas and why they failed.

## Closing prompt

> Draft prompt: return to the central rule: first identify repeated bookkeeping,
> then make the common case representable without it, and retain a simple,
> correct fallback for everything else.

## Figures and code still needed

- [ ] tagged-word bit layout;
- [ ] inline-versus-heap object layout;
- [ ] lifetime diagram for arena/slab/pool allocation;
- [ ] flexible-array allocation layout;
- [ ] inline-cache hit/invalidation flow;
- [ ] copy-on-write ownership trace;
- [ ] reusable state-machine loop;
- [ ] one “sidecar adds work” diagram.
