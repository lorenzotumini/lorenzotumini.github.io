Title: Performance Tricks in C
Date: 2026-08-12
Slug: performance-tricks-in-c
Status: draft
Category: Technical notes
Summary: An outline for an article about less-obvious performance techniques in C and systems programming.

<!--
This is a template, not a finished article. Replace the prompts with prose and
small, standalone C examples. The selected research material lives in
content/notes/performance-tricks-material.md.
-->

## Opening: remove bookkeeping from the hot path

> Draft prompt: establish the intended audience and thesis. The article is not
> about basic Big-O advice; it is about representation, lifetime, ownership,
> lookup, and execution-state choices that experienced systems programmers use
> to make common cases cheap.

## 1. Pointer tagging and immediate values

> Draft prompt: show a tagged `uintptr_t` value that stores small integers in
> the word itself, then explain alignment, range limits, fallback objects,
> equality, hashing, and portability.

Include:

- a bit-layout diagram;
- a checked encode/decode example;
- a note on low-bit tags versus NaN-boxing;
- why the representation must be invisible to callers.

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
