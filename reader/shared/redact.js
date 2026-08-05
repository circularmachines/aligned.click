/* Drawing redactions, once, for both halves of aligned.click.
 *
 * A published turn can have spans the author covered rather than withhold the
 * whole answer over. The record carries three block characters where the words
 * were, so a viewer that does nothing at all shows a redaction already — this
 * paints them as one solid bar instead of a row of glyphs.
 *
 * Nothing here recovers the words. They were never published: the record is
 * written with the bar in place of them.
 *
 * Both sites need the drawing; only the chat needs the bars to be pressable
 * (to put a redaction back), so that is a callback rather than two copies of
 * the walk. `onBar(bar, index)` is called for each bar in document order.
 */
(function () {
  const BLOCK = /█+/g;

  window.paintRedactions = function paintRedactions(root, onBar) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const found = [];
    let node;
    // Collected first: replacing a text node while walking would move the
    // walker out from under itself.
    while ((node = walker.nextNode())) {
      if (node.textContent.includes("█")) found.push(node);
    }
    let n = 0;
    for (const textNode of found) {
      const text = textNode.textContent;
      const frag = document.createDocumentFragment();
      let last = 0;
      BLOCK.lastIndex = 0;
      for (const m of text.matchAll(BLOCK)) {
        if (m.index > last) {
          frag.appendChild(document.createTextNode(text.slice(last, m.index)));
        }
        const bar = document.createElement("span");
        bar.className = "redacted";
        bar.textContent = m[0];
        bar.title = "redacted by the author";
        if (onBar) onBar(bar, n);
        n++;
        frag.appendChild(bar);
        last = m.index + m[0].length;
      }
      if (last < text.length) {
        frag.appendChild(document.createTextNode(text.slice(last)));
      }
      textNode.replaceWith(frag);
    }
  };
})();
