(() => {
  const root = document.documentElement;
  const choices = document.querySelectorAll("[data-look-choice]");
  const mode = document.querySelector(".study-mode");
  const menu = document.querySelector(".location-menu");
  const rhythm = document.querySelector(".rhythm");
  const steps = [...document.querySelectorAll(".rhythm-step")];
  const play = document.querySelector(".rhythm-play");
  const status = document.querySelector(".rhythm-status");
  let audio;
  let running = false;
  let starting = false;
  let timer;
  let step = 0;
  let generation = 0;
  const voices = new Set();

  function stop() {
    generation++;
    if (running && status) status.textContent = "Rhythm stopped.";
    running = false;
    clearTimeout(timer);
    for (const voice of voices) voice.stop();
    voices.clear();
    steps.forEach(button => button.classList.remove("is-playing"));
    if (play) {
      play.innerHTML = 'Play rhythm <span aria-hidden="true">↗</span>';
      play.setAttribute("aria-pressed", "false");
    }
    if (audio?.state === "running") audio.suspend();
  }

  function sound(kick) {
    const oscillator = audio.createOscillator();
    const gain = audio.createGain();
    const now = audio.currentTime;
    oscillator.type = kick ? "sine" : "triangle";
    oscillator.frequency.setValueAtTime(kick ? 130 : 1100, now);
    oscillator.frequency.exponentialRampToValueAtTime(kick ? 45 : 500, now + 0.06);
    gain.gain.setValueAtTime(0, now);
    gain.gain.linearRampToValueAtTime(kick ? 0.22 : 0.07, now + 0.003);
    gain.gain.exponentialRampToValueAtTime(0.001, now + (kick ? 0.14 : 0.045));
    oscillator.connect(gain);
    gain.connect(audio.destination);
    voices.add(oscillator);
    oscillator.onended = () => {
      voices.delete(oscillator);
      oscillator.disconnect();
      gain.disconnect();
    };
    oscillator.start(now);
    oscillator.stop(now + 0.16);
  }

  function tick() {
    if (!running) return;
    steps.forEach((button, index) => button.classList.toggle("is-playing", index === step));
    if (steps[step].getAttribute("aria-pressed") === "true") sound(step % 4 === 0);
    step = (step + 1) % 16;
    timer = setTimeout(tick, 60000 / 96 / 4);
  }

  function sync() {
    choices.forEach(choice => {
      if (choice.dataset.lookChoice === root.dataset.look) choice.setAttribute("aria-current", "true");
      else choice.removeAttribute("aria-current");
    });
    const nextMode = root.dataset.theme === "light" ? "dark" : "light";
    mode.textContent = `${nextMode[0].toUpperCase()}${nextMode.slice(1)} mode`;
    mode.setAttribute("aria-label", `Switch to ${nextMode} mode`);
    if (rhythm) rhythm.hidden = root.dataset.look !== "signal";
    const current = new URL(location.href);
    current.searchParams.set("look", root.dataset.look);
    current.searchParams.set("mode", root.dataset.theme);
    history.replaceState(null, "", current);
    for (const link of document.querySelectorAll("a[href]")) {
      if (link.hasAttribute("data-look-choice")) continue;
      const url = new URL(link.href, location.href);
      if (url.origin !== location.origin || !["http:", "https:"].includes(url.protocol)) continue;
      url.searchParams.set("look", root.dataset.look);
      url.searchParams.set("mode", root.dataset.theme);
      link.href = url;
    }
  }

  for (const choice of choices) {
    choice.addEventListener("click", event => {
      if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      stop();
      root.dataset.look = choice.dataset.lookChoice;
      root.dataset.theme = ["signal", "current"].includes(root.dataset.look) ? "dark" : "light";
      sync();
    });
  }

  mode.addEventListener("click", () => {
    root.dataset.theme = root.dataset.theme === "light" ? "dark" : "light";
    sync();
  });
  document.addEventListener("click", event => {
    if (menu && !menu.contains(event.target)) menu.open = false;
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && menu?.open) {
      menu.open = false;
      menu.querySelector("summary").focus();
    }
  });
  window.addEventListener("pageshow", sync);
  window.addEventListener("pagehide", stop);
  document.addEventListener("visibilitychange", () => { if (document.hidden) stop(); });
  for (const button of steps) {
    button.addEventListener("click", () => {
      button.setAttribute("aria-pressed", String(button.getAttribute("aria-pressed") !== "true"));
    });
  }
  if (play) {
    play.addEventListener("click", async () => {
      if (running) return stop();
      if (starting) return;
      starting = true;
      const request = ++generation;
      try {
        const Audio = window.AudioContext || window.webkitAudioContext;
        if (!Audio) throw new Error("Audio unavailable");
        audio ||= new Audio();
        await audio.resume();
        if (request !== generation || document.hidden || root.dataset.look !== "signal") {
          await audio.suspend();
          return;
        }
        status.textContent = "Rhythm playing.";
        running = true;
        step = 0;
        play.textContent = "Stop rhythm □";
        play.setAttribute("aria-pressed", "true");
        tick();
      } catch (_) {
        status.textContent = "Audio playback is unavailable in this browser.";
        stop();
      } finally {
        starting = false;
      }
    });
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(entries => {
        if (!entries[0].isIntersecting) stop();
      }).observe(rhythm);
    }
  }
  sync();
})();
