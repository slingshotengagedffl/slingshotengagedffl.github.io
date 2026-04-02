(function () {
  const NAV_ITEMS = [
    { emoji: '🏠', label: 'Home',                    href: 'index.html',        external: false },
    { emoji: '💪', label: 'Beefcakes',               href: 'beefcakes.html',    external: false,
      submenu: [
        { label: 'Alex',   href: 'profiles/alex.html' },
        { label: 'Andy',   href: 'profiles/andy.html' },
        { label: 'Brian',  href: 'profiles/brian.html' },
        { label: 'Daniel', href: 'profiles/daniel.html' },
        { label: 'Dylan',  href: 'profiles/dylan.html' },
        { label: 'Jack',   href: 'profiles/jack.html' },
        { label: 'Jordan', href: 'profiles/jordan.html' },
        { label: 'Kyle',   href: 'profiles/kyle.html' },
        { label: 'Luke',   href: 'profiles/luke.html' },
        { label: 'Matt',   href: 'profiles/matt.html' },
        { label: 'Mike',   href: 'profiles/mike.html' },
        { label: 'Scott',  href: 'profiles/scott.html' },
        { label: 'Tim',    href: 'profiles/tim.html' },
        { label: 'Wade',   href: 'profiles/wade.html' },
      ]
    },
    { emoji: '📊', label: 'The Annals',              href: 'annals.html',       external: false,
      submenu: [
        { label: 'Single Season Stats',          href: 'rb-single-season-stats.html' },
        { label: 'Single Game Records',          href: 'rb-single-game-records.html' },
        { label: 'Single Season Records',        href: 'rb-single-season-records.html' },
        { label: 'Career Stats',                 href: 'rb-career-stats.html' },
        { label: 'Career Records',               href: 'rb-career-records.html' },
        { label: 'Career Playoff Records',       href: 'rb-career-playoff-records.html' },
        { label: 'Season Summaries',             href: 'rb-season-summaries.html' },
        { label: 'Prestige Rankings',            href: 'annals-prestige-rankings.html' },
        { label: 'Head-To-Head',                 href: 'rb-head-to-head.html' },
        { label: 'Playoff Odds',                 href: 'rb-playoff-odds.html' },
        { label: 'Draft Position Success',       href: 'rb-draft-position-success.html' },
        { label: 'Correlation To Wins',          href: 'rb-correlation-to-wins.html' },
        { label: 'Lucky / Unlucky',              href: 'rb-lucky-unlucky.html' },
        { label: 'Boom Or Bust',                 href: 'rb-boom-or-bust.html' },
        { label: 'The Streak And The Drought',   href: 'rb-streak-and-drought.html' },
        { label: 'The Intercontinental Championship', href: 'rb-intercontinental-championship.html' },
        { label: 'League Weekends',                  href: 'annals-league-weekends.html' },
      ]
    },
    { emoji: '📋', label: 'Constitution',            href: 'https://drive.google.com/file/d/1u5CjjgncTrwKSedc5rtYRhpPllhlc3w7/view?usp=drivesdk', external: true },
    { emoji: '📸', label: 'Album',                   href: 'https://photos.app.goo.gl/B97a54JNwhCwhof39', external: true },
    { emoji: '🌍', label: "Franks 'Round the World", href: 'https://maps.app.goo.gl/jM1vFzPdmUkwxZN57?g_st=ac', external: true },
  ];

  // Detect if we're in a subfolder (e.g. profiles/)
  const inSubfolder = location.pathname.includes('/profiles/');
  const prefix = inSubfolder ? '../' : '';

  // Determine active page filename
  const currentPage = location.pathname.split('/').pop() || 'index.html';

  // Inject CSS
  const style = document.createElement('style');
  style.textContent = `
    nav {
      display: flex; align-items: center; justify-content: space-between;
      padding: 0 20px; height: 60px; background: #0d0d0d;
      border-bottom: 2px solid var(--red); position: sticky; top: 0; z-index: 100;
    }
    .nav-logo {
      font-family: 'Bebas Neue', sans-serif; font-weight: 400;
      font-size: 1.35rem; letter-spacing: 0.1em;
      color: var(--red-bright); text-transform: uppercase;
    }
    .hotdog-btn {
      background: none; border: none; cursor: pointer;
      font-size: 1.75rem; line-height: 1; padding: 4px; transition: transform 0.2s;
    }
    .hotdog-btn:hover { transform: scale(1.15) rotate(-5deg); }
    .menu-overlay {
      position: fixed; inset: 0; background: rgba(0,0,0,0.6);
      z-index: 200; opacity: 0; pointer-events: none; transition: opacity 0.25s;
    }
    .menu-overlay.open { opacity: 1; pointer-events: all; }
    .slide-menu {
      position: fixed; top: 0; right: 0;
      width: min(340px, 100vw); height: 100vh; background: #0d0d0d;
      border-left: 2px solid var(--red); z-index: 300;
      transform: translateX(100%); transition: transform 0.3s cubic-bezier(0.4,0,0.2,1);
      display: flex; flex-direction: column; overflow-y: auto;
    }
    .slide-menu.open { transform: translateX(0); }
    .slide-menu-header {
      display: flex; align-items: center; justify-content: space-between;
      padding: 0 20px; height: 60px; border-bottom: 2px solid var(--red);
      flex-shrink: 0;
    }
    .close-btn {
      background: none; border: none; color: #666; font-size: 1.5rem;
      cursor: pointer; line-height: 1;
    }
    .close-btn:hover { color: #fff; }
    .menu-items { display: flex; flex-direction: column; }
    .menu-item-row {
      display: flex; align-items: center;
      border-bottom: 1px solid #2a2a2a; transition: background 0.15s;
    }
    .menu-item-row:hover { background: #1a1a1a; }
    .menu-item {
      display: flex; align-items: center; gap: 14px;
      padding: 20px 22px; flex: 1;
      cursor: pointer; text-decoration: none;
    }
    .menu-item-emoji { font-size: 1.4rem; }
    .menu-item-label {
      font-family: 'Bebas Neue', sans-serif; font-weight: 400;
      font-size: 1.2rem; letter-spacing: 0.12em;
      text-transform: uppercase; color: #fff;
    }
    .menu-item.active .menu-item-label { color: var(--red-bright); }
    .submenu-toggle {
      background: none; border: none; cursor: pointer;
      padding: 20px 18px 20px 4px; color: #666;
      font-size: 0.75rem; line-height: 1; transition: color 0.15s;
      flex-shrink: 0;
    }
    .submenu-toggle:hover { color: var(--red-bright); }
    .submenu-toggle.open { color: var(--red-bright); }
    .submenu {
      display: none; flex-direction: column;
      background: #111; border-bottom: 1px solid #2a2a2a;
    }
    .submenu.open { display: flex; }
    .submenu-item {
      display: block; text-decoration: none;
      padding: 12px 22px 12px 52px;
      font-family: 'Bebas Neue', sans-serif; font-weight: 400;
      font-size: 1rem; letter-spacing: 0.12em; text-transform: uppercase;
      color: #aaa; border-bottom: 1px solid #1a1a1a;
      transition: color 0.15s, background 0.15s;
    }
    .submenu-item:last-child { border-bottom: none; }
    .submenu-item:hover { color: #fff; background: #1a1a1a; }
    .submenu-item.active { color: var(--red-bright); }
  `;
  document.head.appendChild(style);

  const nav = document.createElement('nav');
  nav.innerHTML = `
    <div class="nav-logo">Slingshot Engaged</div>
    <button class="hotdog-btn" id="menuToggle" aria-label="Open menu">🌭</button>
  `;

  const overlay = document.createElement('div');
  overlay.className = 'menu-overlay';
  overlay.id = 'menuOverlay';

  const slideMenu = document.createElement('div');
  slideMenu.className = 'slide-menu';
  slideMenu.id = 'slideMenu';

  let menuHTML = `
    <div class="slide-menu-header">
      <div class="nav-logo">Slingshot Engaged</div>
      <button class="close-btn" id="menuClose">✕</button>
    </div>
    <div class="menu-items">
  `;

  NAV_ITEMS.forEach((item, i) => {
    const isActive = !item.external && currentPage === item.href.split('/').pop();
    const href = item.external ? item.href : prefix + item.href;
    const target = item.external ? 'target="_blank" rel="noopener noreferrer"' : '';

    if (item.submenu) {
      menuHTML += `
        <div class="menu-item-row">
          <a href="${href}" class="menu-item${isActive ? ' active' : ''}" ${target}>
            <span class="menu-item-emoji">${item.emoji}</span>
            <span class="menu-item-label">${item.label}</span>
          </a>
          <button class="submenu-toggle" data-index="${i}" aria-label="Expand ${item.label}">▼</button>
        </div>
        <div class="submenu" id="submenu-${i}">
          ${item.submenu.map(sub => {
            const subHref = prefix + sub.href;
            const subActive = currentPage === sub.href.split('/').pop();
            return `<a href="${subHref}" class="submenu-item${subActive ? ' active' : ''}">${sub.label}</a>`;
          }).join('')}
        </div>
      `;
    } else {
      menuHTML += `
        <div class="menu-item-row">
          <a href="${href}" class="menu-item${isActive ? ' active' : ''}" ${target}>
            <span class="menu-item-emoji">${item.emoji}</span>
            <span class="menu-item-label">${item.label}</span>
          </a>
        </div>
      `;
    }
  });

  menuHTML += `</div>`;
  slideMenu.innerHTML = menuHTML;

  document.body.prepend(slideMenu);
  document.body.prepend(overlay);
  document.body.prepend(nav);

  function openMenu() {
    slideMenu.classList.add('open');
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
  }
  function closeMenu() {
    slideMenu.classList.remove('open');
    overlay.classList.remove('open');
    document.body.style.overflow = '';
  }

  document.getElementById('menuToggle').addEventListener('click', openMenu);
  document.getElementById('menuClose').addEventListener('click', closeMenu);
  overlay.addEventListener('click', closeMenu);

  // Submenu toggle arrow ▼ / ▲
  slideMenu.querySelectorAll('.submenu-toggle').forEach(btn => {
    btn.addEventListener('click', function () {
      const index = this.dataset.index;
      const submenu = document.getElementById('submenu-' + index);
      const isOpen = submenu.classList.toggle('open');
      this.classList.toggle('open', isOpen);
      this.textContent = isOpen ? '▲' : '▼';
    });
  });

})();
