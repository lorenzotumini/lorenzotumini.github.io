(() => {
  const bar = document.querySelector(".page-scrollbar");
  const thumb = bar?.querySelector(".page-scrollbar-thumb");

  if (!bar || !thumb) {
    return;
  }

  const thumbLength = 128;
  let frame = 0;
  let drag = null;

  function update() {
    frame = 0;

    const scroller = document.scrollingElement;
    const viewport = window.innerHeight;
    const maxScroll = Math.max(0, scroller.scrollHeight - viewport);

    if (maxScroll === 0) {
      bar.hidden = true;
      return null;
    }

    bar.hidden = false;

    const trackLength = bar.clientHeight;
    const height = Math.min(thumbLength, trackLength);
    const maxTop = Math.max(0, trackLength - height);
    const top = maxTop * (scroller.scrollTop / maxScroll);

    thumb.style.height = `${height}px`;
    thumb.style.transform = `translateY(${top}px)`;

    return { maxScroll, maxTop };
  }

  function scheduleUpdate() {
    if (!frame) {
      frame = requestAnimationFrame(update);
    }
  }

  window.addEventListener("scroll", scheduleUpdate, { passive: true });
  window.addEventListener("resize", scheduleUpdate);
  window.addEventListener("load", update);

  if ("ResizeObserver" in window) {
    new ResizeObserver(scheduleUpdate).observe(document.body);
  }

  thumb.addEventListener("pointerdown", (event) => {
    const metrics = update();

    if (!metrics || metrics.maxTop === 0) {
      return;
    }

    event.preventDefault();
    thumb.setPointerCapture(event.pointerId);
    drag = {
      pointerId: event.pointerId,
      startY: event.clientY,
      startScroll: document.scrollingElement.scrollTop,
      ...metrics,
    };
  });

  thumb.addEventListener("pointermove", (event) => {
    if (!drag || event.pointerId !== drag.pointerId) {
      return;
    }

    const distance = event.clientY - drag.startY;
    const scrollTop =
      drag.startScroll + distance * (drag.maxScroll / drag.maxTop);

    window.scrollTo({ top: scrollTop, behavior: "auto" });
  });

  function stopDragging(event) {
    if (!drag || event.pointerId !== drag.pointerId) {
      return;
    }

    drag = null;
  }

  thumb.addEventListener("pointerup", stopDragging);
  thumb.addEventListener("pointercancel", stopDragging);

  update();
})();
