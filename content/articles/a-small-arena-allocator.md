Title: A small arena allocator in C
Date: 2026-07-25
Slug: a-small-arena-allocator
Summary: An arena is little more than a buffer and an offset. That constraint is exactly what makes it useful.

General-purpose allocators solve a difficult problem: memory may be requested
and returned in almost any order. Many programs contain smaller regions where
that flexibility is unnecessary. If a group of objects shares a lifetime, they
can share an allocator too.

An arena reserves one contiguous block of memory. Allocation moves a cursor
forward; releasing every object at once moves it back to the beginning.

<figure class="technical-figure">
  <div
    class="memory-diagram"
    role="img"
    aria-label="A memory buffer with 38 percent allocated and 62 percent free"
  >
    <span class="memory-used">allocated</span>
    <span class="memory-free">free</span>
  </div>
  <figcaption>
    The allocator only needs to remember where the used region ends.
  </figcaption>
</figure>

## What the arena keeps

A minimal representation needs three values:

```c
typedef struct {
    unsigned char *base;
    size_t offset;
    size_t capacity;
} Arena;
```

`base` points to the beginning of the buffer, `capacity` records its total
size, and `offset` identifies the first unused byte.

## Allocation

Before advancing the offset, it must be rounded up to satisfy the requested
alignment. The allocation fails if the aligned region would extend beyond the
capacity.

```c
void *arena_alloc(Arena *arena, size_t size, size_t alignment)
{
    size_t mask = alignment - 1;
    size_t start = (arena->offset + mask) & ~mask;

    if (start > arena->capacity ||
        size > arena->capacity - start) {
        return NULL;
    }

    arena->offset = start + size;
    return arena->base + start;
}
```

This version assumes that alignment is a non-zero power of two. A production
implementation should either validate that precondition or make it explicit in
its interface.

## Resetting and trade-offs

Resetting the arena is a single assignment: `arena->offset = 0`. Individual
allocations cannot be freed, and destructors are not called automatically.
Those are not missing features; they are the rules that make the allocator
predictable.

> Use the narrowest allocator that matches the lifetime of the data.

Arenas work particularly well for parsers, per-frame data, temporary compiler
structures, and request-scoped objects. They are less suitable when allocations
must survive independently or when the maximum working set is difficult to
estimate.

The full implementation would add initialization, overflow checks, optional
zeroing, and tests. The central idea, however, remains a pointer moving through
a buffer.
