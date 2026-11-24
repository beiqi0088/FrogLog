/* ============================================================
   DOM → SVG 导出器
   把当前渲染的某一屏，序列化成「Figma 可编辑」的 SVG：
   - 每个盒子 → <rect>（含圆角、填充、描边）
   - 每行文字 → <text>（保留字体/字号/字重/颜色/对齐）
   - 图表    → 直接克隆原 <svg>
   - 渐变    → <linearGradient> / <radialGradient>
   用法：index.html?only=today&export=svg
   ============================================================ */
(function () {
  const W = 390, H = 844;

  const esc = (s) => String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');

  function parseColor(c) {
    if (!c) return null;
    const m = c.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(',').map(v => parseFloat(v.trim()));
    const [r, g, b] = p;
    const a = p.length > 3 ? p[3] : 1;
    if (a === 0) return null;
    return { hex: '#' + [r, g, b].map(v => Math.round(v).toString(16).padStart(2, '0')).join(''), a };
  }

  const num = (v) => Math.round(v * 100) / 100;

  let uid = 0;
  const defs = [];

  function gradientFor(kind, box) {
    const id = 'g' + (++uid);
    if (kind === 'hero') {
      defs.push(`<linearGradient id="${id}" x1="0" y1="0" x2="0.5" y2="1">
        <stop offset="0" stop-color="#245637"/><stop offset="1" stop-color="#2F6A43"/></linearGradient>`);
      return `url(#${id})`;
    }
    if (kind === 'heroGlow') {
      defs.push(`<radialGradient id="${id}" cx="100%" cy="0%" r="120%">
        <stop offset="0" stop-color="#2F6A43" stop-opacity="0.55"/>
        <stop offset="0.55" stop-color="#2F6A43" stop-opacity="0"/></radialGradient>`);
      return `url(#${id})`;
    }
    if (kind === 'primary') {
      defs.push(`<linearGradient id="${id}" x1="0" y1="0" x2="0.34" y2="1">
        <stop offset="0" stop-color="#2F6A43"/><stop offset="1" stop-color="#245637"/></linearGradient>`);
      return `url(#${id})`;
    }
    if (kind === 'orb') {
      defs.push(`<radialGradient id="${id}" cx="34%" cy="30%" r="62%">
        <stop offset="0" stop-color="#2F6A43" stop-opacity="0.34"/>
        <stop offset="1" stop-color="#2F6A43" stop-opacity="0"/></radialGradient>`);
      return `url(#${id})`;
    }
    if (kind === 'todayBar') {
      defs.push(`<linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#2F6A43"/><stop offset="1" stop-color="#245637"/></linearGradient>`);
      return `url(#${id})`;
    }
    if (kind === 'cardBar') {
      defs.push(`<linearGradient id="${id}" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="#2F6A43"/><stop offset="1" stop-color="#BF5B38"/></linearGradient>`);
      return `url(#${id})`;
    }
    return null;
  }

  /** 元素的圆角半径（取四个角的最大值，按需裁到半宽高） */
  function radiusOf(cs, w, h) {
    const vals = [cs.borderTopLeftRadius, cs.borderTopRightRadius,
                  cs.borderBottomRightRadius, cs.borderBottomLeftRadius]
      .map(v => parseFloat(v) || 0);
    let r = Math.max(...vals);
    r = Math.min(r, w / 2, h / 2);
    return r > 0.5 ? r : 0;
  }

  function rectFor(x, y, w, h, r, fill, fillOpacity, stroke, strokeW, opacity) {
    if (w <= 0.2 || h <= 0.2) return '';
    const attrs = [
      `x="${num(x)}"`, `y="${num(y)}"`, `width="${num(w)}"`, `height="${num(h)}"`,
      r ? `rx="${num(r)}"` : '',
      fill ? `fill="${fill}"` : 'fill="none"',
      fill && fillOpacity != null && fillOpacity < 1 ? `fill-opacity="${num(fillOpacity)}"` : '',
      stroke ? `stroke="${stroke}"` : '',
      stroke ? `stroke-width="${num(strokeW)}"` : '',
      opacity != null && opacity < 1 ? `opacity="${num(opacity)}"` : '',
    ].filter(Boolean).join(' ');
    return `<rect ${attrs}/>`;
  }

  function walk(el, ctx, out) {
    if (!el || el.nodeType !== 1) return;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;

    const r = el.getBoundingClientRect();
    const x = r.left - ctx.ox, y = r.top - ctx.oy, w = r.width, h = r.height;

    // 原生 SVG（雷达/环/图标）直接克隆
    if (el.tagName.toLowerCase() === 'svg') {
      const clone = el.cloneNode(true);
      clone.setAttribute('x', num(x));
      clone.setAttribute('y', num(y));
      clone.setAttribute('width', num(w));
      clone.setAttribute('height', num(h));
      out.push(`<g id="${esc(el.dataset.layer || 'icon')}">${clone.outerHTML}</g>`);
      return;
    }

    const cls = el.className && typeof el.className === 'string' ? el.className : '';
    const name = el.dataset.layer || (cls.split(' ')[0] || el.tagName.toLowerCase());

    // ---- 背景 ----
    let opacity = parseFloat(cs.opacity);
    if (isNaN(opacity)) opacity = 1;

    // 特殊：Tab 选中指示条（原为 ::before）
    if (/tabbar/.test(el.parentElement?.className || '') &&
        el.dataset.on === 'true' && el.tagName === 'BUTTON') {
      const cx = x + w / 2;
      out.push(`<g id="tab-indicator">${rectFor(cx - 11, y + 2, 22, 2.5, 1.25, '#2F6A43', 1, null, 0, opacity)}</g>`);
    }

    const gradKind = el.dataset.grad;
    if (gradKind) {
      const fill = gradientFor(gradKind, { x, y, w, h });
      const rad = radiusOf(cs, w, h);
      out.push(`<g id="${esc(name)}-bg">${rectFor(x, y, w, h, rad, fill, 1, null, 0, opacity)}</g>`);
      if (gradKind === 'hero') {
        const glow = gradientFor('heroGlow', { x, y, w, h });
        out.push(`<g id="${esc(name)}-glow">${rectFor(x, y, w, h, rad, glow, 1, null, 0, opacity)}</g>`);
      }
    } else {
      const bg = parseColor(cs.backgroundColor);
      if (bg) {
        const rad = radiusOf(cs, w, h);
        out.push(rectFor(x, y, w, h, rad, bg.hex, bg.a * opacity, null, 0, null));
      }
    }

    // ---- 描边 ----
    const bw = parseFloat(cs.borderTopWidth) || 0;
    if (bw > 0 && cs.borderTopStyle !== 'none') {
      const bc = parseColor(cs.borderTopColor);
      if (bc) {
        const rad = radiusOf(cs, w, h);
        out.push(rectFor(x + bw / 2, y + bw / 2, w - bw, h - bw, Math.max(0, rad - bw / 2),
          null, 0, bc.hex, bw, bc.a * opacity));
      }
    }

    // ---- 文字（按行拆成 <text>）----
    for (const node of el.childNodes) {
      if (node.nodeType !== 3) continue;
      const text = node.textContent;
      if (!text || !text.trim()) continue;

      const range = document.createRange();
      range.selectNodeContents(node);
      const rects = Array.from(range.getClientRects()).filter(q => q.width > 0.5 && q.height > 0.5);
      const color = parseColor(cs.color) || { hex: '#000000', a: 1 };
      const fs = parseFloat(cs.fontSize);
      const fw = cs.fontWeight;
      const ff = cs.fontFamily;
      const lh = parseFloat(cs.lineHeight) || fs * 1.3;
      const align = cs.textAlign;
      const ls = cs.letterSpacing === 'normal' ? 0 : parseFloat(cs.letterSpacing) || 0;

      for (const q of rects) {
        const rx = q.left - ctx.ox;
        // 基线近似：行盒中心 + 0.3em
        const ry = q.top - ctx.oy + q.height / 2 + fs * 0.3;
        let anchor = 'start', tx = rx;
        if (align === 'center') { anchor = 'middle'; tx = rx + q.width / 2; }
        else if (align === 'right' || align === 'end') { anchor = 'end'; tx = rx + q.width; }

        out.push(`<text x="${num(tx)}" y="${num(ry)}" fill="${color.hex}"` +
          (color.a < 1 ? ` fill-opacity="${num(color.a * opacity)}"` : '') +
          ` font-family="${esc(ff)}" font-size="${num(fs)}" font-weight="${fw}"` +
          (ls ? ` letter-spacing="${num(ls)}"` : '') +
          ` text-anchor="${anchor}"${opacity < 1 && color.a === 1 ? ` opacity="${num(opacity)}"` : ''}` +
          ` xml:space="preserve">${esc(text.trim())}</text>`);
      }
    }

    // ---- 装饰：门禁页同心圆 ----
    if (cls.includes('orb')) {
      const cx = x + w / 2, cy = y + h / 2, rr = w / 2;
      out.push(`<g id="orb-rings" fill="none" stroke="#E4E1D6">
        <circle cx="${num(cx)}" cy="${num(cy)}" r="${num(rr + 22)}" opacity="0.6"/>
        <circle cx="${num(cx)}" cy="${num(cy)}" r="${num(rr + 46)}" opacity="0.32"/></g>`);
    }

    // ---- 装饰：复习卡顶部渐变条（原为 ::before）----
    if (cls.includes('flashcard')) {
      const grad = gradientFor('cardBar', { x, y, w, h });
      out.push(`<g id="flashcard-topbar">${rectFor(x, y, w, 3, 0, grad, 0.75, null, 0, opacity)}</g>`);
    }

    // ---- 滚动容器：裁剪 + 子层递归 ----
    const scrollable = cs.overflowY === 'auto' || cs.overflowY === 'scroll' || cs.overflow === 'hidden';
    if (scrollable && el.children.length) {
      const cid = 'clip' + (++uid);
      defs.push(`<clipPath id="${cid}"><rect x="${num(x)}" y="${num(y)}" width="${num(w)}" height="${num(h)}" rx="${num(radiusOf(cs, w, h))}"/></clipPath>`);
      const inner = [];
      for (const ch of el.children) walk(ch, ctx, inner);
      out.push(`<g id="${esc(name)}-content" clip-path="url(#${cid})">${inner.join('')}</g>`);
      return;
    }

    for (const ch of el.children) walk(ch, ctx, out);
  }

  /** 给需要渐变的元素打标记，序列化时按标记生成 gradient */
  function tagGradients(root) {
    const set = (sel, kind, all) => {
      const els = all ? root.querySelectorAll(sel) : [root.querySelector(sel)].filter(Boolean);
      els.forEach(e => e.setAttribute('data-grad', kind));
    };
    set('.hero', 'hero');
    set('.consent-art .orb', 'orb');
    set('.btn-primary', 'primary', true);
    set('.bar[data-today="true"]', 'todayBar', true);
  }

  function buildFor(key) {
    const host = document.createElement('div');
    host.style.cssText = 'position:fixed;left:-2000px;top:0;width:390px;height:844px;';
    host.innerHTML = `<div class="device" style="width:390px;height:844px;border:0;border-radius:0;box-shadow:none;background:var(--bg)">${SCREENS[key].fn()}</div>`;
    document.body.appendChild(host);

    const dev = host.firstElementChild;
    tagGradients(dev);
    const dr = dev.getBoundingClientRect();
    const ctx = { ox: dr.left, oy: dr.top };
    const out = [];
    for (const ch of dev.children) walk(ch, ctx, out);

    const bg = parseColor(getComputedStyle(dev).backgroundColor) || { hex: '#FBF8F1' };
    const svg =
      `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">` +
      `<defs>${defs.join('')}</defs>` +
      `<rect width="${W}" height="${H}" fill="${bg.hex}"/>` +
      `<g id="screen-${key}">${out.join('')}</g>` +
      `</svg>`;

    host.remove();
    return svg;
  }

  // 入口：替换整页为单屏 SVG
  const key = new URLSearchParams(location.search).get('only');
  if (key && SCREENS[key]) {
    document.documentElement.dataset.theme =
      new URLSearchParams(location.search).get('theme') || 'light';
    const svg = buildFor(key);
    document.body.innerHTML = `<div id="svg-host">${svg}</div>`;
    document.body.style.cssText = 'margin:0;background:#fff;';
    window.__SVG__ = svg;
  }
})();
