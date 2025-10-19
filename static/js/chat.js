(() => {
  "use strict";

  const elements = {
    searchInput: document.getElementById("destination-search"),
    suggestionsList: document.getElementById("search-suggestions"),
    suggestionsWrapper: document.getElementById("search-suggestions-wrapper"),
    messagesContainer: document.getElementById("messages"),
    emptyState: document.getElementById("empty-state"),
    composerForm: document.getElementById("composer"),
    chatInput: document.getElementById("chat-input"),
    sendButton: document.getElementById("send-button"),
    toastRegion: document.getElementById("toast-region"),
    searchToggle: document.getElementById("search-toggle"),
    searchPanel: document.getElementById("search-panel"),
    chatLog: document.getElementById("chat-log"),
  };

  if (
    !elements.searchInput ||
    !elements.suggestionsList ||
    !elements.messagesContainer ||
    !elements.emptyState ||
    !elements.composerForm ||
    !elements.chatInput ||
    !elements.sendButton
  ) {
    return;
  }

  const fallbackScript = document.getElementById("fallback-destinations");
  let fallbackDestinations = [];
  if (fallbackScript) {
    try {
      fallbackDestinations = JSON.parse(fallbackScript.textContent || "[]");
    } catch (error) {
      console.error("Failed to parse fallback destinations", error);
      fallbackDestinations = [];
    }
    fallbackScript.remove();
  }
  fallbackDestinations.sort(
    (a, b) => (b.popularity_score || 0) - (a.popularity_score || 0)
  );

  const state = {
    fallbackDestinations,
    suggestions: [],
    activeIndex: -1,
    searchAbort: null,
    lastSearchQuery: "",
    lastSearchSource: "fallback",
    lastSearchResults: fallbackDestinations.slice(),
    messageKeys: new Set(),
    lastTimestamp: null,
    pollTimer: null,
  };

  const config = {
    searchDebounce: 300,
    pollInterval: 4000,
  };

  function stripDiacritics(value) {
    if (!value) return "";
    try {
      return value.normalize("NFD").replace(/\p{Diacritic}/gu, "");
    } catch (error) {
      return value;
    }
  }

  const normalize = (value) => stripDiacritics(String(value || "").toLowerCase());

  function levenshtein(a, b, maxDistance = 2) {
    if (a === b) return 0;
    if (Math.abs(a.length - b.length) > maxDistance) return maxDistance + 1;
    if (!a.length) return b.length;
    if (!b.length) return a.length;
    if (a.length > b.length) [a, b] = [b, a];

    const previous = new Array(b.length + 1).fill(0).map((_, i) => i);
    for (let i = 1; i <= a.length; i += 1) {
      const current = [i];
      let rowMin = current[0];
      const charA = a[i - 1];
      for (let j = 1; j <= b.length; j += 1) {
        const charB = b[j - 1];
        const insertCost = current[j - 1] + 1;
        const deleteCost = previous[j] + 1;
        const substituteCost = previous[j - 1] + (charA === charB ? 0 : 1);
        const best = Math.min(insertCost, deleteCost, substituteCost);
        current.push(best);
        if (best < rowMin) rowMin = best;
      }
      if (rowMin > maxDistance) return maxDistance + 1;
      for (let j = 0; j < previous.length; j += 1) {
        previous[j] = current[j];
      }
    }
    return previous[previous.length - 1];
  }

  function runLocalSearch(query, limit = 20) {
    const normalizedQuery = normalize(query);
    const scored = [];

    state.fallbackDestinations.forEach((item) => {
      const combined = [
        item.name,
        item.city,
        item.country,
        item.short_desc,
      ]
        .filter(Boolean)
        .join(" ");
      const normalizedCombined = normalize(combined);

      let distance = 0;
      let matches = false;

      if (!normalizedQuery) {
        matches = true;
      } else if (normalizedCombined.includes(normalizedQuery)) {
        matches = true;
      } else {
        const nameNorm = normalize(item.name || "").slice(0, 40);
        distance = levenshtein(normalizedQuery.slice(0, 40), nameNorm, 2);
        matches = distance <= 2;
      }

      if (matches) {
        scored.push({ item, distance });
      }
    });

    scored.sort((a, b) => {
      const popularityDelta = (b.item.popularity_score || 0) - (a.item.popularity_score || 0);
      if (popularityDelta !== 0) return popularityDelta;
      return a.distance - b.distance;
    });

    return scored.slice(0, limit).map((entry) => ({ ...entry.item }));
  }

  function debounce(fn, delay) {
    let timer;
    function debounced(...args) {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => {
        fn.apply(null, args);
      }, delay);
    }
    debounced.flush = (...args) => {
      window.clearTimeout(timer);
      fn.apply(null, args);
    };
    return debounced;
  }

  const debouncedSearch = debounce(executeSearch, config.searchDebounce);

  async function executeSearch(query) {
    const trimmed = query.trim();
    state.lastSearchQuery = trimmed;

    if (state.searchAbort) {
      state.searchAbort.abort();
    }

    if (!trimmed) {
      state.lastSearchSource = "fallback";
      state.lastSearchResults = state.fallbackDestinations.slice();
      state.suggestions = state.lastSearchResults.slice(0, 6);
      state.activeIndex = -1;
      updateSuggestions();
      return;
    }

    const controller = new AbortController();
    state.searchAbort = controller;

    try {
      const params = new URLSearchParams({ q: trimmed, limit: "20" });
      const response = await fetch(`/api/search?${params.toString()}`, {
        signal: controller.signal,
      });
      if (!response.ok) {
        throw new Error(`Search failed with status ${response.status}`);
      }
      const data = await response.json();
      if (controller.signal.aborted) return;
      const hits = Array.isArray(data.hits) ? data.hits : [];
      state.lastSearchResults = hits;
      state.lastSearchSource = data.source || "fallback";
      state.suggestions = hits.slice(0, 8);
      state.activeIndex = hits.length ? 0 : -1;
      updateSuggestions();
    } catch (error) {
      if (controller.signal.aborted) return;
      console.warn("Falling back to local search", error);
      showToast("Search unavailable. Using local suggestions.", "warning");
      const localResults = runLocalSearch(trimmed, 20);
      state.lastSearchResults = localResults;
      state.lastSearchSource = "client-fallback";
      state.suggestions = localResults.slice(0, 8);
      state.activeIndex = localResults.length ? 0 : -1;
      updateSuggestions();
    } finally {
      state.searchAbort = null;
    }
  }

  function requestSearch(query, { immediate = false } = {}) {
    if (immediate) {
      executeSearch(query).catch((error) => console.error(error));
    } else {
      debouncedSearch(query);
    }
  }

  function updateSuggestions() {
    elements.suggestionsList.innerHTML = "";
    const shouldShow = state.suggestions.length > 0;
    elements.suggestionsList.classList.toggle("hidden", !shouldShow);
    elements.searchInput.setAttribute("aria-expanded", String(shouldShow));

    if (!shouldShow) {
      elements.searchInput.setAttribute("aria-activedescendant", "");
      return;
    }

    state.suggestions.forEach((suggestion, index) => {
      const option = createSuggestionOption(suggestion, index);
      elements.suggestionsList.appendChild(option);
    });

    if (state.activeIndex >= 0) {
      setActiveSuggestion(state.activeIndex);
    }
  }

  function createSuggestionOption(suggestion, index) {
    const option = document.createElement("li");
    option.id = `suggestion-option-${index}`;
    option.setAttribute("role", "option");
    option.dataset.index = String(index);
    option.className = "flex cursor-pointer items-center gap-3 px-3 py-2 text-sm text-slate-700 hover:bg-indigo-50 focus:bg-indigo-100 aria-selected:bg-indigo-100 dark:text-slate-200 dark:hover:bg-indigo-500/20";

    const thumbnail = document.createElement("div");
    thumbnail.className = "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-blue-400 font-semibold text-white";
    if (suggestion.hero_image_url) {
      const img = document.createElement("img");
      img.src = suggestion.hero_image_url;
      img.alt = `${suggestion.name || ""} thumbnail`;
      img.className = "h-9 w-9 rounded-lg object-cover";
      thumbnail.replaceChildren(img);
    } else if (suggestion.name) {
      thumbnail.textContent = String(suggestion.name).slice(0, 2).toUpperCase();
    } else {
      thumbnail.textContent = "?";
    }

    const meta = document.createElement("div");
    meta.className = "min-w-0 flex-1";

    const title = document.createElement("p");
    title.className = "truncate font-medium text-slate-900 dark:text-slate-100";
    title.textContent = suggestion.name || "Unknown";

    const subtitle = document.createElement("p");
    subtitle.className = "truncate text-xs text-slate-500 dark:text-slate-400";
    subtitle.textContent = [suggestion.city, suggestion.country].filter(Boolean).join(", ");

    const chip = document.createElement("span");
    chip.className = "shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-200";
    chip.textContent = `★ ${suggestion.popularity_score ?? "-"}`;

    meta.appendChild(title);
    if (subtitle.textContent) meta.appendChild(subtitle);

    option.appendChild(thumbnail);
    option.appendChild(meta);
    option.appendChild(chip);

    option.addEventListener("mousedown", (event) => {
      event.preventDefault();
      handleSuggestionSelection(index);
    });

    option.addEventListener("mousemove", () => {
      if (state.activeIndex !== index) {
        setActiveSuggestion(index, { scroll: false });
      }
    });

    return option;
  }

  function setActiveSuggestion(index, { scroll = true } = {}) {
    const options = elements.suggestionsList.querySelectorAll("[role=option]");
    options.forEach((option, optionIndex) => {
      const isActive = optionIndex === index;
      option.setAttribute("aria-selected", String(isActive));
      option.classList.toggle("bg-indigo-100", isActive);
      option.classList.toggle("dark:bg-indigo-500/20", isActive);
      if (isActive && scroll) {
        option.scrollIntoView({ block: "nearest" });
      }
    });
    state.activeIndex = index;
    const activeOption = options[index];
    if (activeOption) {
      elements.searchInput.setAttribute("aria-activedescendant", activeOption.id);
    } else {
      elements.searchInput.setAttribute("aria-activedescendant", "");
    }
  }

  function handleSuggestionSelection(index) {
    const suggestion = state.suggestions[index];
    if (!suggestion) return;

    elements.searchInput.value = suggestion.name || state.lastSearchQuery;
    closeSuggestions();
    elements.searchInput.blur();

    pushDestinationToChat(suggestion, `Searching: ${suggestion.name}`);
  }

  function closeSuggestions() {
    state.suggestions = [];
    state.activeIndex = -1;
    elements.suggestionsList.innerHTML = "";
    elements.suggestionsList.classList.add("hidden");
    elements.searchInput.setAttribute("aria-expanded", "false");
    elements.searchInput.setAttribute("aria-activedescendant", "");
  }

  function pushDestinationToChat(destination, text) {
    if (!destination) {
      postMessage({ role: "system", text }).then(({ message }) => {
        appendMessages(filterTruthy([message]));
      }).catch((error) => {
        console.error("Failed to post system message", error);
        showToast("We could not log the system update.", "error");
      });
      return;
    }

    const card = {
      title: destination.name,
      subtitle: [destination.city, destination.country].filter(Boolean).join(", "),
      popularity: destination.popularity_score,
      short_desc: destination.short_desc,
      hero_image_url: destination.hero_image_url,
    };

    if (!state.lastSearchResults.some((item) => item.id === destination.id)) {
      state.lastSearchResults = [destination, ...state.lastSearchResults].slice(0, 20);
    }

    postMessage({ role: "system", text, card })
      .then(({ message }) => {
        appendMessages(filterTruthy([message]));
      })
      .catch((error) => {
        console.error("Failed to post system message", error);
        showToast("We could not log the system update.", "error");
      });
  }

  function showToast(message, variant = "info") {
    if (!elements.toastRegion) return;
    const toast = document.createElement("div");
    toast.className = "pointer-events-auto rounded-lg border px-4 py-3 text-sm shadow-lg backdrop-blur transition";

    const styles = {
      info: "border-slate-200 bg-white/90 text-slate-800 dark:border-slate-700 dark:bg-slate-900/90 dark:text-slate-100",
      warning: "border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-500/60 dark:bg-amber-500/10 dark:text-amber-100",
      error: "border-rose-300 bg-rose-50 text-rose-700 dark:border-rose-500/60 dark:bg-rose-500/10 dark:text-rose-100",
    };

    toast.className += ` ${styles[variant] || styles.info}`;
    toast.setAttribute("role", "status");
    toast.textContent = message;

    elements.toastRegion.appendChild(toast);
    window.setTimeout(() => {
      toast.classList.add("opacity-0", "translate-y-2");
      window.setTimeout(() => toast.remove(), 220);
    }, 4500);
  }

  function buildMessageKey(message) {
    return [message.createdAt, message.role, message.text].join("|");
  }

  function appendMessages(messages) {
    let appended = false;
    messages.forEach((message) => {
      if (!message || !message.createdAt || !message.role) return;
      const key = buildMessageKey(message);
      if (state.messageKeys.has(key)) return;
      state.messageKeys.add(key);
      elements.messagesContainer.appendChild(renderMessage(message));
      appended = true;
      state.lastTimestamp = message.createdAt;
    });
    if (appended) {
      updateEmptyState();
      scrollMessagesToBottom();
    }
  }

  function renderMessage(message) {
    const wrapper = document.createElement("div");
    wrapper.className = "flex";

    const bubble = document.createElement("div");
    bubble.className = "max-w-full rounded-2xl px-4 py-3 text-sm shadow-sm transition";
    bubble.setAttribute("dir", "auto");
    bubble.dataset.role = message.role;

    if (message.role === "user") {
      wrapper.classList.add("justify-end");
      bubble.classList.add("bg-indigo-600", "text-white");
    } else if (message.role === "assistant") {
      wrapper.classList.add("justify-start");
      bubble.classList.add("bg-slate-900/90", "text-slate-100", "dark:bg-slate-800/90");
    } else {
      wrapper.classList.add("justify-center");
      bubble.classList.add("bg-slate-200/80", "text-slate-700", "dark:bg-slate-800/80", "dark:text-slate-100");
    }

    if (message.text) {
      const textNode = document.createElement("p");
      textNode.textContent = message.text;
      bubble.appendChild(textNode);
    }

    if (message.card) {
      bubble.appendChild(renderCard(message.card));
    }

    wrapper.appendChild(bubble);
    return wrapper;
  }

  function renderCard(card) {
    const container = document.createElement("section");
    container.className = "mt-3 w-full rounded-xl border border-slate-200 bg-white p-4 text-left dark:border-slate-700 dark:bg-slate-900";
    container.setAttribute("aria-label", card.title || "Destination insight");

    if (card.hero_image_url) {
      const img = document.createElement("img");
      img.src = card.hero_image_url;
      img.alt = card.title ? `${card.title} highlight` : "Destination hero";
      img.className = "mb-3 h-32 w-full rounded-lg object-cover";
      container.appendChild(img);
    }

    const heading = document.createElement("h3");
    heading.className = "text-base font-semibold text-slate-900 dark:text-slate-100";
    heading.textContent = card.title || "Destination";

    const subtitle = document.createElement("p");
    subtitle.className = "text-sm text-slate-500 dark:text-slate-400";
    subtitle.textContent = card.subtitle || "";

    const badge = document.createElement("span");
    badge.className = "mt-2 inline-flex items-center rounded-full bg-indigo-100 px-2 py-1 text-xs font-medium text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-200";
    badge.textContent = `Popularity ${card.popularity ?? "-"}`;

    const description = document.createElement("p");
    description.className = "mt-3 text-sm text-slate-600 dark:text-slate-300";
    description.textContent = card.short_desc || "";
    description.setAttribute("dir", "auto");

    container.appendChild(heading);
    if (subtitle.textContent) container.appendChild(subtitle);
    container.appendChild(badge);
    if (description.textContent) container.appendChild(description);

    return container;
  }

  function updateEmptyState() {
    const hasMessages = state.messageKeys.size > 0;
    elements.emptyState.classList.toggle("hidden", hasMessages);
  }

  function scrollMessagesToBottom() {
    if (!elements.chatLog) return;
    elements.chatLog.scrollTo({ top: elements.chatLog.scrollHeight, behavior: "smooth" });
  }

  function filterTruthy(list) {
    return list.filter(Boolean);
  }

  async function postMessage(payload) {
    const response = await fetch("/api/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `Message failed with ${response.status}`);
    }
    return response.json();
  }

  async function sendUserMessage() {
    const text = (elements.chatInput.value || "").trim();
    if (!text) return;

    elements.sendButton.disabled = true;
    elements.chatInput.value = "";

    try {
      const { message, assistant } = await postMessage({ role: "user", text });
      appendMessages(filterTruthy([message, assistant]));
    } catch (error) {
      console.error("Failed to send message", error);
      showToast("We could not send your message. Try again.", "error");
      elements.chatInput.value = text;
    } finally {
      elements.sendButton.disabled = false;
      elements.chatInput.focus();
    }
  }

  async function loadInitialMessages() {
    try {
      const response = await fetch("/api/messages");
      if (!response.ok) return;
      const data = await response.json();
      appendMessages(Array.isArray(data.messages) ? data.messages : []);
    } catch (error) {
      console.warn("Unable to load previous messages", error);
    }
  }

  async function pollMessages() {
    if (!state.lastTimestamp) return;
    try {
      const params = new URLSearchParams({ since: state.lastTimestamp });
      const response = await fetch(`/api/messages?${params.toString()}`);
      if (!response.ok) return;
      const data = await response.json();
      appendMessages(Array.isArray(data.messages) ? data.messages : []);
    } catch (error) {
      console.warn("Failed to poll messages", error);
    }
  }

  function schedulePolling() {
    if (state.pollTimer) window.clearInterval(state.pollTimer);
    state.pollTimer = window.setInterval(pollMessages, config.pollInterval);
  }

  function setupEventListeners() {
    elements.searchInput.addEventListener("input", (event) => {
      const value = event.target.value;
      requestSearch(value);
    });

    elements.searchInput.addEventListener("keydown", (event) => {
      switch (event.key) {
        case "ArrowDown":
          event.preventDefault();
          if (!state.suggestions.length) return;
          setActiveSuggestion(
            state.activeIndex < state.suggestions.length - 1
              ? state.activeIndex + 1
              : 0
          );
          break;
        case "ArrowUp":
          event.preventDefault();
          if (!state.suggestions.length) return;
          setActiveSuggestion(
            state.activeIndex > 0
              ? state.activeIndex - 1
              : state.suggestions.length - 1
          );
          break;
        case "Enter":
          if (state.suggestions.length && state.activeIndex >= 0) {
            event.preventDefault();
            handleSuggestionSelection(state.activeIndex);
          }
          break;
        case "Escape":
          closeSuggestions();
          break;
        default:
          break;
      }
    });

    elements.composerForm.addEventListener("submit", (event) => {
      event.preventDefault();
      sendUserMessage();
    });

    elements.chatInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendUserMessage();
      }
    });

    document.querySelectorAll(".quick-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        const query = chip.getAttribute("data-quick-query") || "";
        elements.searchInput.value = query;
        const localResults = runLocalSearch(query, 20);
        state.lastSearchResults = localResults;
        state.suggestions = localResults.slice(0, 8);
        state.activeIndex = localResults.length ? 0 : -1;
        updateSuggestions();
        requestSearch(query, { immediate: true });
        pushDestinationToChat(localResults[0], `Searching: ${query}`);
        elements.chatInput.focus();
      });
    });

    if (elements.searchToggle && elements.searchPanel) {
      elements.searchToggle.addEventListener("click", () => {
        const isHidden = elements.searchPanel.classList.contains("hidden");
        if (isHidden) {
          elements.searchPanel.classList.remove("hidden");
          elements.searchToggle.setAttribute("aria-expanded", "true");
          elements.searchInput.focus();
        } else {
          elements.searchPanel.classList.add("hidden");
          elements.searchToggle.setAttribute("aria-expanded", "false");
        }
      });

      const desktopMedia = window.matchMedia("(min-width: 768px)");
      const handleMediaChange = (event) => {
        if (event.matches) {
          elements.searchPanel.classList.remove("hidden");
          elements.searchToggle?.setAttribute("aria-expanded", "true");
        } else {
          elements.searchPanel.classList.add("hidden");
          elements.searchToggle?.setAttribute("aria-expanded", "false");
        }
      };
      handleMediaChange(desktopMedia);
      desktopMedia.addEventListener("change", handleMediaChange);

      document.addEventListener("click", (event) => {
        if (
          !elements.searchPanel.contains(event.target) &&
          !elements.searchToggle.contains(event.target) &&
          window.matchMedia("(max-width: 767px)").matches
        ) {
          elements.searchPanel.classList.add("hidden");
          elements.searchToggle.setAttribute("aria-expanded", "false");
        }
      });
    }
  }

  function initSuggestions() {
    state.suggestions = state.fallbackDestinations.slice(0, 6);
    updateSuggestions();
  }

  function init() {
    initSuggestions();
    setupEventListeners();
    loadInitialMessages().then(() => {
      schedulePolling();
    });
  }

  init();
})();
