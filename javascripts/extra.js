(function () {
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const revealNodes = (root) => {
    if (prefersReducedMotion) return;
    const targets = root.querySelectorAll(".reveal:not(.in-view)");
    if (!targets.length) return;

    if (!("IntersectionObserver" in window)) {
      targets.forEach((node) => node.classList.add("in-view"));
      return;
    }

    const observer = new IntersectionObserver(
      (entries, obs) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("in-view");
            obs.unobserve(entry.target);
          }
        });
      },
      {
        root: null,
        threshold: 0.14,
        rootMargin: "0px 0px -40px 0px"
      }
    );

    targets.forEach((node) => observer.observe(node));
  };

  const cssVar = (name, fallback) => {
    const value = getComputedStyle(document.body).getPropertyValue(name).trim();
    return value || fallback;
  };

  const syncMermaidBlocks = (root) => {
    root.querySelectorAll("pre code.language-mermaid, pre code.mermaid").forEach((code) => {
      const pre = code.closest("pre");
      if (!pre) return;

      const block = document.createElement("div");
      block.className = "mermaid";
      block.textContent = code.textContent || "";
      pre.replaceWith(block);
    });
  };

  const renderMermaid = async (root) => {
    if (typeof window.mermaid === "undefined") return;

    syncMermaidBlocks(root);
    const blocks = root.querySelectorAll(".mermaid");
    if (!blocks.length) return;

    const darkMode = document.body.getAttribute("data-md-color-scheme") === "slate";
    window.mermaid.initialize({
      startOnLoad: false,
      securityLevel: "loose",
      theme: "base",
      themeVariables: {
        primaryColor: cssVar("--mermaid-node-bg", darkMode ? "#132a2f" : "#f0fdfa"),
        primaryBorderColor: cssVar("--mermaid-node-border", darkMode ? "#35d0a0" : "#0b5f4a"),
        primaryTextColor: cssVar("--text-strong", darkMode ? "#f8fafc" : "#0f172a"),
        secondaryColor: cssVar("--langgraph-cyan", "#22d3ee"),
        tertiaryColor: cssVar("--langgraph-violet", "#7c3aed"),
        lineColor: cssVar("--mermaid-edge", darkMode ? "#67e8f9" : "#0891b2"),
        clusterBkg: cssVar("--mermaid-cluster-bg", darkMode ? "#1a2942" : "#e0f2fe"),
        clusterBorder: cssVar("--mermaid-node-border", darkMode ? "#35d0a0" : "#0b5f4a"),
        fontFamily: "inherit"
      },
      flowchart: {
        curve: "basis"
      }
    });

    blocks.forEach((block) => block.removeAttribute("data-processed"));
    await window.mermaid.run({ querySelector: ".mermaid" });
  };

  const initEnhancements = () => {
    revealNodes(document);
    renderMermaid(document).catch((error) => {
      console.warn("Mermaid render failed:", error);
    });
  };

  if (typeof document$ !== "undefined") {
    document$.subscribe(initEnhancements);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initEnhancements);
  } else {
    initEnhancements();
  }

  if (typeof MutationObserver !== "undefined") {
    const observer = new MutationObserver((changes) => {
      const schemeChanged = changes.some(
        (change) =>
          change.type === "attributes" &&
          change.attributeName === "data-md-color-scheme"
      );
      if (schemeChanged) {
        renderMermaid(document).catch((error) => {
          console.warn("Mermaid theme refresh failed:", error);
        });
      }
    });
    observer.observe(document.body, {
      attributes: true,
      attributeFilter: ["data-md-color-scheme"]
    });
  }
})();
