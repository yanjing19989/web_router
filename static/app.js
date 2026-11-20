    const icons = {
      play: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 5v14l11-7L8 5Z"/></svg>',
      stop: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="6" width="12" height="12" rx="1"/></svg>',
      open: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 4h6v6m0-6-9 9"/><path d="M19 13v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h5"/></svg>',
      folder: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/><path d="M3 9h18"/></svg>',
      edit: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m14 5 5 5M4 20l3.5-.7L19 7.8a2.1 2.1 0 0 0-3-3L4.7 16.3 4 20Z"/></svg>',
      trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 7h16M9 7V4h6v3m3 0-1 13H7L6 7m4 4v5m4-5v5"/></svg>',
      grip: '<svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><circle cx="5.5" cy="3.5" r="1.25"/><circle cx="10.5" cy="3.5" r="1.25"/><circle cx="5.5" cy="8" r="1.25"/><circle cx="10.5" cy="8" r="1.25"/><circle cx="5.5" cy="12.5" r="1.25"/><circle cx="10.5" cy="12.5" r="1.25"/></svg>',
      chevron: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>'
    };

    const typeMeta = {
      npm: {
        label: 'Node.js / npm 项目',
        svg: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10.8 2.1Q12 1.4 13.2 2.1L20 6Q21.2 6.7 21.2 8.1V15.9Q21.2 17.3 20 18L13.2 21.9Q12 22.6 10.8 21.9L4 18Q2.8 17.3 2.8 15.9V8.1Q2.8 6.7 4 6Z" fill="#46a049"/><path d="M10.8 2.1Q12 1.4 13.2 2.1L20 6Q20.6 6.35 20.9 6.88L12 12L3.1 6.88Q3.4 6.35 4 6Z" fill="#fff" fill-opacity=".14"/><path d="M20.9 6.88Q21.2 7.4 21.2 8.1V15.9Q21.2 17.3 20 18L13.2 21.9Q12.6 22.25 12 22.25V12Z" fill="#0b3d12" fill-opacity=".16"/><path d="M9.4 8.45h1.6v5.2c0 1.85-1.05 2.8-2.75 2.8-.95 0-1.65-.28-2.15-.78l.78-1.36c.35.34.76.54 1.24.54.82 0 1.28-.45 1.28-1.32v-5.08Zm8.15.95c-.65-.75-1.6-1.1-2.75-1.1-1.6 0-2.65.95-2.65 2.25 0 1.3.9 1.9 2.35 2.28 1.2.3 1.68.56 1.68 1.22 0 .6-.55.98-1.38.98-.86 0-1.56-.33-2.03-.9l-.92 1.18c.65.8 1.7 1.25 3 1.25 1.8 0 3-.98 3-2.45 0-1.38-.9-1.98-2.45-2.36-1.18-.3-1.62-.55-1.62-1.18 0-.54.47-.84 1.14-.84.7 0 1.28.27 1.7.74l.93-1.07Z" fill="#144d1a" fill-opacity=".28"/><path d="M9.4 8h1.6v5.2c0 1.85-1.05 2.8-2.75 2.8-.95 0-1.65-.28-2.15-.78l.78-1.36c.35.34.76.54 1.24.54.82 0 1.28-.45 1.28-1.32V8Zm8.15.95c-.65-.75-1.6-1.1-2.75-1.1-1.6 0-2.65.95-2.65 2.25 0 1.3.9 1.9 2.35 2.28 1.2.3 1.68.56 1.68 1.22 0 .6-.55.98-1.38.98-.86 0-1.56-.33-2.03-.9l-.92 1.18c.65.8 1.7 1.25 3 1.25 1.8 0 3-.98 3-2.45 0-1.38-.9-1.98-2.45-2.36-1.18-.3-1.62-.55-1.62-1.18 0-.54.47-.84 1.14-.84.7 0 1.28.27 1.7.74l.93-1.07Z" fill="#fff"/></svg>'
      },
      python: {
        label: 'Python 项目',
        svg: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M11.9 2C8.3 2 7.4 3.5 7.4 5.05V6.7H12V7.4H5.5C3.45 7.4 2 8.8 2 11.95C2 15.1 3.35 16.6 5.25 16.6H6.7V14.5C6.7 12.4 8.1 11.55 10.2 11.55H13.8C15.6 11.55 16.6 10.65 16.6 9.15V5.05C16.6 3.3 15.3 2 11.9 2Z" fill="#377ab3"/><path d="M2 11.95C2 15.1 3.35 16.6 5.25 16.6H6.7V14.5C6.7 12.4 8.1 11.55 10.2 11.55H13.8C15.6 11.55 16.6 10.65 16.6 9.15V8.1C16.1 9.6 15.1 10.4 13.5 10.4H10C7.5 10.4 5.8 11.7 5.8 14.2V15.5H5.25C3.7 15.5 2.4 14.4 2 11.95Z" fill="#1e4f7a" fill-opacity=".26"/><path d="M12.1 22C15.7 22 16.6 20.5 16.6 18.95V17.3H12V16.6H18.5C20.55 16.6 22 15.2 22 12.05C22 8.9 20.65 7.4 18.75 7.4H17.3V9.5C17.3 11.6 15.9 12.45 13.8 12.45H10.2C8.4 12.45 7.4 13.35 7.4 14.85V18.95C7.4 20.7 8.7 22 12.1 22Z" fill="#ffd43b"/><path d="M16.6 17.8V18.95C16.6 20.5 15.7 22 12.1 22C8.7 22 7.4 20.7 7.4 18.95V18C7.9 19.7 9.2 20.8 12.1 20.8C14.8 20.8 15.7 19.8 16.6 17.8ZM22 12.05C22 15.2 20.55 16.6 18.5 16.6H12V15.5H18.3C19.9 15.5 21.4 14.5 22 12.05Z" fill="#d99100" fill-opacity=".24"/><circle cx="9.5" cy="4.45" r=".95" fill="#fff"/><circle cx="14.5" cy="19.55" r=".95" fill="#fff"/></svg>'
      },
      static: {
        label: '静态站点',
        svg: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10" fill="#0ea5e9"/><path d="M19.07 4.93A10 10 0 0 1 4.93 19.07A11.5 11.5 0 0 0 19.07 4.93Z" fill="#0369a1" fill-opacity=".34"/><ellipse cx="8.5" cy="7.2" rx="3.4" ry="2.1" transform="rotate(-32 8.5 7.2)" fill="#fff" fill-opacity=".22"/><g fill="none" stroke="#fff" stroke-opacity=".92" stroke-width="1.45" stroke-linecap="round"><ellipse cx="12" cy="12" rx="4.3" ry="9.2"/><path d="M2.8 12h18.4M4.1 7.4Q12 9.4 19.9 7.4M4.1 16.6Q12 14.6 19.9 16.6"/></g></svg>'
      }
    };

    const COMPACT_STORAGE_KEY = 'web_router.compact_mode';

    function loadCompactMode() {
      try {
        return window.localStorage.getItem(COMPACT_STORAGE_KEY) === '1';
      } catch (_) {
        return false;
      }
    }

    function saveCompactMode(enabled) {
      try {
        window.localStorage.setItem(COMPACT_STORAGE_KEY, enabled ? '1' : '0');
      } catch (_) {}
    }

    const state = {
      projects: [],
      refreshing: false,
      loaded: false,
      hasRunningProjects: false,
      selectingText: false,
      dragging: false,
      reordering: false,
      compact: loadCompactMode(),
      expandedIds: new Set(),
      editingId: null,
      actionIds: new Set(),
      filterTypes: new Set(['npm', 'python', 'static']),
      pollTimer: null
    };
    const content = document.querySelector('#project-content');
    const dialog = document.querySelector('#project-dialog');
    const form = document.querySelector('#project-form');
    const addButton = document.querySelector('#add-project');
    const compactButton = document.querySelector('#toggle-compact');

    async function api(url, options = {}) {
      const response = await fetch(url, {
        ...options,
        headers: options.body ? { 'Content-Type': 'application/json', ...(options.headers || {}) } : options.headers
      });
      if (!response.ok) {
        let message = `请求失败（${response.status}）`;
        try {
          const body = await response.json();
          if (body.detail) message = body.detail;
        } catch (_) {}
        throw new Error(message);
      }
      return response.status === 204 ? null : response.json();
    }

    function showToast(message, type = '') {
      const toast = document.createElement('div');
      toast.className = `toast ${type}`;
      toast.textContent = message;
      document.querySelector('#toasts').append(toast);
      window.setTimeout(() => toast.remove(), 3800);
    }

    function formatBytes(bytes) {
      if (!bytes) return '0 MB';
      const units = ['B', 'KB', 'MB', 'GB'];
      const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
      const value = bytes / Math.pow(1024, index);
      return `${value.toFixed(index < 2 ? 0 : 1)} ${units[index]}`;
    }

    function formatDuration(seconds) {
      if (!seconds) return '—';
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      const rest = seconds % 60;
      if (hours) return `${hours}时 ${minutes}分`;
      if (minutes) return `${minutes}分 ${rest}秒`;
      return `${rest}秒`;
    }

    function setText(element, value, withTitle = false) {
      if (element.textContent !== value) element.textContent = value;
      if (withTitle && element.title !== value) element.title = value;
    }

    function syncCompactMode() {
      document.body.classList.toggle('compact-mode', state.compact);
      compactButton.classList.toggle('active', state.compact);
      compactButton.setAttribute('aria-pressed', String(state.compact));
      compactButton.title = state.compact ? '切换为详细视图' : '切换为紧凑视图';
    }

    function metric(label, value) {
      const wrapper = document.createElement('div');
      wrapper.className = 'metric';
      const dt = document.createElement('dt');
      const dd = document.createElement('dd');
      dt.textContent = label;
      dd.textContent = value;
      dd.title = value;
      wrapper.append(dt, dd);
      return { wrapper, valueEl: dd };
    }

    function compactStat(label) {
      const item = document.createElement('span');
      item.textContent = label;
      const valueEl = document.createElement('strong');
      valueEl.textContent = '—';
      item.append(valueEl);
      return { item, valueEl };
    }

    function detailRow(label, value) {
      const row = document.createElement('div');
      row.className = 'detail-row';
      const name = document.createElement('span');
      name.className = 'detail-label';
      name.textContent = label;
      const text = document.createElement('code');
      text.className = 'detail-value';
      text.textContent = value;
      text.title = value;
      row.append(name, text);
      return { row, valueEl: text };
    }

    function actionButton(label, action, icon, classes = '', iconOnly = false) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = `button ${classes}`.trim();
      button.dataset.action = action;
      button.innerHTML = icon;
      if (iconOnly) {
        button.setAttribute('aria-label', label);
        button.title = label;
      } else {
        const text = document.createElement('span');
        text.textContent = label;
        button.append(text);
      }
      return button;
    }

    function escapeSvgText(text) {
      return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function initialIconSvg(name) {
      const first = Array.from((name || '').trim())[0];
      const letter = first ? first.toUpperCase() : '?';
      return `<svg viewBox="0 0 28 28" aria-hidden="true"><rect width="28" height="28" rx="7" fill="var(--accent-soft)"/><text x="14" y="15" text-anchor="middle" dominant-baseline="central" fill="var(--accent)" font-size="15" font-weight="700" font-family="inherit">${escapeSvgText(letter)}</text></svg>`;
    }

    function updateProjectIcon(container, project) {
      const first = Array.from((project.name || '').trim())[0];
      const letter = first ? first.toUpperCase() : '?';
      const iconKey = project.icon_url ? `img:${project.icon_url}` : `letter:${letter}`;
      if (container.dataset.iconKey === iconKey) return;
      container.dataset.iconKey = iconKey;
      if (project.icon_url) {
        const img = document.createElement('img');
        img.src = project.icon_url;
        img.alt = '';
        img.decoding = 'async';
        img.onerror = () => {
          container.dataset.iconKey = `letter:${letter}`;
          container.innerHTML = initialIconSvg(project.name);
        };
        container.replaceChildren(img);
      } else {
        container.innerHTML = initialIconSvg(project.name);
      }
    }

    function updateCard(card, project) {
      const refs = card._refs;
      const running = project.status === 'running';
      const busy = state.actionIds.has(project.id);
      const expanded = state.expandedIds.has(project.id);

      card.classList.toggle('running', running);
      card.classList.toggle('expanded', expanded);
      refs.expand.setAttribute('aria-expanded', String(expanded));
      const expandTitle = expanded ? '收起详情' : '展开详情';
      if (refs.expand.title !== expandTitle) {
        refs.expand.title = expandTitle;
        refs.expand.setAttribute('aria-label', expandTitle);
      }

      updateProjectIcon(refs.icon, project);
      setText(refs.name, project.name);
      if (refs.typeKey !== project.type) {
        refs.typeKey = project.type;
        const meta = typeMeta[project.type];
        if (meta) {
          refs.type.innerHTML = meta.svg;
          refs.type.title = meta.label;
          refs.type.setAttribute('aria-label', meta.label);
        } else {
          refs.type.textContent = project.type;
          refs.type.title = project.type;
          refs.type.setAttribute('aria-label', project.type);
        }
      }
      setText(refs.port, `:${project.port}`);
      const portTitle = `端口 ${project.port}`;
      if (refs.port.title !== portTitle) refs.port.title = portTitle;

      const statusClass = `status ${project.status}`;
      if (refs.status.className !== statusClass) refs.status.className = statusClass;
      setText(refs.status, running ? '运行中' : '已停止');

      const pidText = project.pid ? String(project.pid) : '—';
      const cpuText = running ? `${project.cpu_percent.toFixed(1)}%` : '—';
      const ussText = running ? formatBytes(project.memory_uss_bytes) : '—';
      const vmsText = running ? formatBytes(project.memory_vms_bytes) : '—';

      setText(refs.compactPid, pidText);
      setText(refs.compactCpu, cpuText);
      setText(refs.compactUss, ussText);
      setText(refs.compactVms, vmsText);

      setText(refs.pid, pidText, true);
      setText(refs.cpu, cpuText, true);
      setText(refs.uss, ussText, true);
      setText(refs.vms, vmsText, true);

      setText(refs.uptime, formatDuration(project.uptime_seconds), true);
      setText(refs.url, project.url, true);
      setText(refs.path, project.path, true);
      setText(refs.command, project.command, true);

      const primaryMode = busy ? 'busy' : (running ? 'stop' : 'start');
      if (refs.primaryMode !== primaryMode) {
        refs.primaryMode = primaryMode;
        refs.primary.dataset.action = running ? 'stop' : 'start';
        refs.primary.className = `button ${running ? 'button-danger' : 'button-primary'}`.trim();
        refs.primary.disabled = busy;
        refs.primary.innerHTML = busy
          ? '<span class="spinner" aria-hidden="true"></span><span>处理中</span>'
          : `${running ? icons.stop : icons.play}<span>${running ? '停止' : '启动'}</span>`;
      }
      refs.open.disabled = !running;
      refs.edit.disabled = running;
      const editTitle = running ? '请先停止项目再编辑' : '编辑项目';
      if (refs.edit.title !== editTitle) refs.edit.title = editTitle;
      refs.remove.disabled = running;
    }

    function renderCard(project) {
      const card = document.createElement('article');
      card.className = 'project-card';
      card.dataset.id = project.id;

      const head = document.createElement('div');
      head.className = 'project-head';

      const handle = document.createElement('button');
      handle.type = 'button';
      handle.className = 'drag-handle';
      handle.setAttribute('aria-label', '拖拽排序');
      handle.title = '拖拽排序';
      handle.innerHTML = icons.grip;

      const title = document.createElement('div');
      title.className = 'project-title';
      const icon = document.createElement('span');
      icon.className = 'project-icon';
      icon.setAttribute('aria-hidden', 'true');
      const h3 = document.createElement('h3');
      const typeLine = document.createElement('div');
      typeLine.className = 'type-line';
      const type = document.createElement('span');
      type.className = 'type-badge';
      const port = document.createElement('span');
      port.className = 'port-badge';
      typeLine.append(type, port);
      title.append(icon, h3, typeLine);

      const headEnd = document.createElement('div');
      headEnd.className = 'project-head-end';
      const status = document.createElement('span');
      const expand = document.createElement('button');
      expand.type = 'button';
      expand.className = 'expand-toggle';
      expand.dataset.action = 'toggle-expand';
      expand.setAttribute('aria-expanded', 'false');
      expand.innerHTML = icons.chevron;
      headEnd.append(status, expand);
      head.append(handle, title, headEnd);

      const compactPid = compactStat('PID');
      const compactCpu = compactStat('CPU');
      const compactUss = compactStat('专用');
      const compactVms = compactStat('虚拟');
      const compactMetrics = document.createElement('div');
      compactMetrics.className = 'compact-metrics';
      compactMetrics.append(compactPid.item, compactCpu.item, compactUss.item, compactVms.item);

      const pid = metric('PID', '—');
      const cpu = metric('CPU', '—');
      const uss = metric('专用内存', '—');
      const vms = metric('虚拟内存', '—');
      const metrics = document.createElement('dl');
      metrics.className = 'metrics';
      metrics.append(pid.wrapper, cpu.wrapper, uss.wrapper, vms.wrapper);

      const uptime = detailRow('运行', '—');
      const url = detailRow('地址', '');
      const path = detailRow('路径', '');
      const command = detailRow('命令', '');
      const details = document.createElement('div');
      details.className = 'details';
      details.append(uptime.row, url.row, path.row, command.row);

      const cardBody = document.createElement('div');
      cardBody.className = 'card-body';
      const cardBodyInner = document.createElement('div');
      cardBodyInner.className = 'card-body-inner';
      cardBodyInner.append(metrics, details);
      cardBody.append(cardBodyInner);

      const actions = document.createElement('div');
      actions.className = 'project-actions';
      const primary = actionButton('启动', 'start', icons.play, 'button-primary');
      const open = actionButton('打开', 'open', icons.open);
      const folder = actionButton('打开所在目录', 'open-folder', icons.folder, 'icon-only', true);
      const edit = actionButton('编辑项目', 'edit', icons.edit, 'icon-only', true);
      const remove = actionButton('删除项目', 'delete', icons.trash, 'button-danger icon-only', true);
      actions.append(primary, open, folder, edit, remove);
      card.append(head, compactMetrics, cardBody, actions);

      card._refs = {
        icon,
        name: h3,
        type,
        typeKey: '',
        port,
        status,
        expand,
        compactPid: compactPid.valueEl,
        compactCpu: compactCpu.valueEl,
        compactUss: compactUss.valueEl,
        compactVms: compactVms.valueEl,
        pid: pid.valueEl,
        cpu: cpu.valueEl,
        uss: uss.valueEl,
        vms: vms.valueEl,
        uptime: uptime.valueEl,
        url: url.valueEl,
        path: path.valueEl,
        command: command.valueEl,
        primary,
        primaryMode: '',
        open,
        edit,
        remove
      };
      updateCard(card, project);
      return card;
    }

    function syncPolling() {
      const shouldPoll = !document.hidden && state.hasRunningProjects;
      if (shouldPoll && !state.pollTimer) {
        state.pollTimer = window.setInterval(() => refresh(true), 2000);
      } else if (!shouldPoll && state.pollTimer) {
        window.clearInterval(state.pollTimer);
        state.pollTimer = null;
      }
    }

    function render(payload) {
      state.projects = payload.projects;
      state.loaded = true;
      state.hasRunningProjects = payload.summary.running > 0;
      syncPolling();
      setText(document.querySelector('#total-count'), String(payload.summary.total));
      setText(document.querySelector('#running-count'), String(payload.summary.running));
      setText(document.querySelector('#memory-uss-total'), formatBytes(payload.summary.total_memory_uss_bytes));
      setText(document.querySelector('#memory-vms-total'), formatBytes(payload.summary.total_memory_vms_bytes));

      const visibleProjects = payload.projects.filter(project => state.filterTypes.has(project.type));
      if (!visibleProjects.length) {
        content.replaceChildren();
        if (payload.projects.length) {
          const empty = document.createElement('div');
          empty.className = 'empty';
          const message = document.createElement('p');
          message.textContent = '当前筛选类别暂无项目';
          empty.append(message);
          content.append(empty);
          return;
        }
        content.append(document.querySelector('#empty-template').content.cloneNode(true));
        return;
      }

      let grid = content.firstElementChild;
      if (!grid || !grid.classList.contains('project-grid') || !grid.querySelector('.project-card')) {
        grid = document.createElement('div');
        grid.className = 'project-grid';
        visibleProjects.forEach(project => grid.append(renderCard(project)));
        content.replaceChildren(grid);
        return;
      }

      const existing = new Map();
      grid.querySelectorAll(':scope > .project-card').forEach(card => {
        existing.set(card.dataset.id, card);
      });
      const visibleIds = new Set(visibleProjects.map(project => project.id));
      existing.forEach((card, id) => {
        if (!visibleIds.has(id)) card.remove();
      });

      visibleProjects.forEach((project, index) => {
        let card = existing.get(project.id);
        if (card) {
          updateCard(card, project);
        } else {
          card = renderCard(project);
        }
        const currentAt = grid.children[index];
        if (currentAt !== card) {
          grid.insertBefore(card, currentAt || null);
        }
      });
    }

    function renderCurrentState() {
      render({
        summary: {
          total: state.projects.length,
          running: state.projects.filter(item => item.status === 'running').length,
          total_memory_uss_bytes: state.projects.reduce((sum, item) => sum + item.memory_uss_bytes, 0),
          total_memory_vms_bytes: state.projects.reduce((sum, item) => sum + item.memory_vms_bytes, 0)
        },
        projects: state.projects
      });
    }

    function updateProjectFilters() {
      const allSelected = state.filterTypes.size === 3;
      document.querySelectorAll('#project-filters [data-filter]').forEach(button => {
        const type = button.dataset.filter;
        const selected = type === 'all' ? allSelected : state.filterTypes.has(type);
        button.classList.toggle('active', selected);
        button.setAttribute('aria-pressed', String(selected));
      });
    }

    function handleFilter(button) {
      const type = button.dataset.filter;
      if (type === 'all') {
        state.filterTypes = new Set(['npm', 'python', 'static']);
      } else if (state.filterTypes.has(type)) {
        if (state.filterTypes.size === 1) return;
        state.filterTypes.delete(type);
      } else {
        state.filterTypes.add(type);
      }
      updateProjectFilters();
      renderCurrentState();
    }

    function toggleCardExpand(card) {
      if (!state.compact) return;
      const id = card.dataset.id;
      if (state.expandedIds.has(id)) {
        state.expandedIds.delete(id);
      } else {
        state.expandedIds.add(id);
      }
      const project = state.projects.find(item => item.id === id);
      if (project) updateCard(card, project);
    }

    function flipReorder(grid, moveFn) {
      const cards = Array.from(grid.children);
      const firstRects = new Map(cards.map(el => [el, el.getBoundingClientRect()]));
      moveFn();
      cards.forEach(el => {
        if (el.classList.contains('drag-placeholder')) return;
        const first = firstRects.get(el);
        const last = el.getBoundingClientRect();
        const dx = first.left - last.left;
        const dy = first.top - last.top;
        if (!dx && !dy) return;
        el.style.transition = 'none';
        el.style.transform = `translate3d(${dx}px, ${dy}px, 0)`;
        el.getBoundingClientRect();
        el.style.transition = 'transform .18s cubic-bezier(.2, 0, 0, 1)';
        el.style.transform = '';
      });
    }

    function mergeVisibleOrder(projects, visibleIds) {
      const visibleSet = new Set(visibleIds);
      let cursor = 0;
      return projects.map(item => (visibleSet.has(item.id) ? visibleIds[cursor++] : item.id));
    }

    async function persistOrder(visibleIds) {
      const previousProjects = state.projects;
      const mergedIds = mergeVisibleOrder(previousProjects, visibleIds);
      const byId = new Map(previousProjects.map(item => [item.id, item]));
      state.projects = mergedIds.map(id => byId.get(id)).filter(Boolean);
      state.reordering = true;
      try {
        const payload = await api('/api/projects/reorder', {
          method: 'PUT',
          body: JSON.stringify({ ids: mergedIds })
        });
        render(payload);
      } catch (error) {
        state.projects = previousProjects;
        renderCurrentState();
        showToast(error.message, 'error');
      } finally {
        state.reordering = false;
      }
    }

    function startDrag(event, handle) {
      if (event.button !== 0 || state.dragging || state.reordering) return;
      const card = handle.closest('.project-card');
      const grid = card && card.parentElement;
      if (!card || !grid || grid.children.length < 2) return;

      event.preventDefault();
      state.dragging = true;
      const pointerId = event.pointerId;
      const startX = event.clientX;
      const startY = event.clientY;
      const rect = card.getBoundingClientRect();
      const initialCards = Array.from(grid.children);
      const initialIds = initialCards.map(el => el.dataset.id);

      const ghost = card.cloneNode(true);
      ghost.classList.add('drag-ghost');
      ghost.style.width = `${rect.width}px`;
      ghost.style.height = `${rect.height}px`;
      ghost.style.left = `${rect.left}px`;
      ghost.style.top = `${rect.top}px`;
      ghost.style.transform = 'translate3d(0, 0, 0) scale(1.02)';
      document.body.append(ghost);

      card.classList.add('drag-placeholder');
      document.body.classList.add('is-dragging');
      try { handle.setPointerCapture(pointerId); } catch (_) {}

      const findTarget = (clientX, clientY) => {
        const gridRect = grid.getBoundingClientRect();
        const x = clientX - gridRect.left;
        const y = clientY - gridRect.top;
        for (const sibling of grid.children) {
          if (sibling === card) continue;
          const left = sibling.offsetLeft;
          const top = sibling.offsetTop;
          if (x >= left && x <= left + sibling.offsetWidth && y >= top && y <= top + sibling.offsetHeight) {
            return sibling;
          }
        }
        return null;
      };

      const onMove = moveEvent => {
        if (moveEvent.pointerId !== pointerId) return;
        const dx = moveEvent.clientX - startX;
        const dy = moveEvent.clientY - startY;
        ghost.style.transform = `translate3d(${dx}px, ${dy}px, 0) scale(1.02)`;

        if (moveEvent.clientY < 64) window.scrollBy(0, -12);
        else if (moveEvent.clientY > window.innerHeight - 64) window.scrollBy(0, 12);

        const target = findTarget(moveEvent.clientX, moveEvent.clientY);
        if (!target) return;
        const children = Array.from(grid.children);
        const cardIndex = children.indexOf(card);
        const targetIndex = children.indexOf(target);
        if (cardIndex < 0 || targetIndex < 0 || cardIndex === targetIndex) return;
        flipReorder(grid, () => {
          grid.insertBefore(card, cardIndex < targetIndex ? target.nextSibling : target);
        });
      };

      const finish = cancelled => {
        window.removeEventListener('pointermove', onMove);
        window.removeEventListener('pointerup', onUp);
        window.removeEventListener('pointercancel', onCancel);
        window.removeEventListener('keydown', onKeyDown);
        try { handle.releasePointerCapture(pointerId); } catch (_) {}

        ghost.remove();
        card.classList.remove('drag-placeholder');
        document.body.classList.remove('is-dragging');
        Array.from(grid.children).forEach(el => {
          el.style.transition = '';
          el.style.transform = '';
        });
        state.dragging = false;

        if (cancelled) {
          flipReorder(grid, () => {
            initialCards.forEach(el => grid.append(el));
          });
          return;
        }
        const nextIds = Array.from(grid.children).map(el => el.dataset.id);
        if (nextIds.some((id, index) => id !== initialIds[index])) {
          persistOrder(nextIds);
        }
      };

      const onUp = upEvent => {
        if (upEvent.pointerId === pointerId) finish(false);
      };
      const onCancel = cancelEvent => {
        if (cancelEvent.pointerId === pointerId) finish(true);
      };
      const onKeyDown = keyEvent => {
        if (keyEvent.key === 'Escape') finish(true);
      };

      window.addEventListener('pointermove', onMove);
      window.addEventListener('pointerup', onUp);
      window.addEventListener('pointercancel', onCancel);
      window.addEventListener('keydown', onKeyDown);
    }

    function hasActiveSelection() {
      if (state.selectingText) return true;
      const selection = window.getSelection();
      return Boolean(
        selection &&
        !selection.isCollapsed &&
        selection.anchorNode &&
        content.contains(selection.anchorNode)
      );
    }

    async function refresh(silent = false, force = false) {
      if (
        state.refreshing ||
        state.dragging ||
        state.reordering ||
        (!force && state.loaded && (document.hidden || !state.hasRunningProjects || hasActiveSelection()))
      ) return;
      state.refreshing = true;
      try {
        const payload = await api('/api/projects');
        if (!state.dragging && !state.reordering && (force || !hasActiveSelection())) render(payload);
      } catch (error) {
        if (!silent) showToast(error.message, 'error');
      } finally {
        state.refreshing = false;
      }
    }

    function openProjectDialog(project, detector, editingId = null) {
      state.editingId = editingId;
      form.reset();
      document.querySelector('#dialog-title').textContent = editingId ? '编辑项目信息' : '确认项目信息';
      document.querySelector('#dialog-description').textContent = editingId
        ? '修改后的配置将在下次启动时生效。'
        : '自动识别完成后，你可以在保存前修正配置。';
      document.querySelector('#detector').textContent = detector;
      document.querySelector('#project-path').textContent = project.path;
      document.querySelector('#path-input').value = project.path;
      document.querySelector('#name-input').value = project.name;
      document.querySelector('#type-input').value = project.type;
      document.querySelector('#command-input').value = project.command;
      document.querySelector('#port-input').value = project.port;
      document.querySelector('#save-project').textContent = editingId ? '保存修改' : '保存项目';
      dialog.showModal();
      document.querySelector('#name-input').focus();
    }

    async function beginAdd() {
      const original = addButton.innerHTML;
      addButton.disabled = true;
      addButton.innerHTML = '<span class="spinner" aria-hidden="true"></span><span>选择中</span>';
      try {
        const picked = await api('/api/picker', { method: 'POST' });
        if (!picked.path) return;
        addButton.innerHTML = '<span class="spinner" aria-hidden="true"></span><span>识别中</span>';
        const detected = await api('/api/projects/inspect', {
          method: 'POST',
          body: JSON.stringify({ path: picked.path })
        });
        openProjectDialog(detected, detected.detector);
      } catch (error) {
        showToast(error.message, 'error');
      } finally {
        addButton.disabled = false;
        addButton.innerHTML = original;
      }
    }

    async function saveProject(event) {
      event.preventDefault();
      if (!form.reportValidity()) return;
      const button = document.querySelector('#save-project');
      const original = button.innerHTML;
      button.disabled = true;
      button.innerHTML = '<span class="spinner" aria-hidden="true"></span><span>保存中</span>';
      const data = new FormData(form);
      const editingId = state.editingId;
      try {
        await api(editingId ? `/api/projects/${editingId}` : '/api/projects', {
          method: editingId ? 'PUT' : 'POST',
          body: JSON.stringify({
            path: data.get('path'),
            name: data.get('name'),
            type: data.get('type'),
            command: data.get('command'),
            port: Number(data.get('port'))
          })
        });
        dialog.close();
        showToast(editingId ? '项目配置已更新' : '项目已添加');
        await refresh(true, true);
      } catch (error) {
        showToast(error.message, 'error');
      } finally {
        button.disabled = false;
        button.innerHTML = original;
      }
    }

    async function handleAction(button) {
      const card = button.closest('.project-card');
      if (!card) return;
      const id = card.dataset.id;
      const action = button.dataset.action;
      if (action === 'toggle-expand') {
        toggleCardExpand(card);
        return;
      }
      const project = state.projects.find(item => item.id === id);
      if (!project) return;
      if (action === 'open') {
        window.open(project.url, '_blank', 'noopener,noreferrer');
        return;
      }
      if (action === 'open-folder') {
        try {
          await api(`/api/projects/${id}/open-folder`, { method: 'POST' });
          showToast('已打开项目目录');
        } catch (error) {
          showToast(error.message, 'error');
        }
        return;
      }
      if (action === 'edit') {
        openProjectDialog(project, '已有配置', project.id);
        return;
      }
      if (action === 'delete' && !window.confirm(`确定删除“${project.name}”吗？`)) return;

      state.actionIds.add(id);
      renderCurrentState();
      try {
        if (action === 'delete') {
          await api(`/api/projects/${id}`, { method: 'DELETE' });
          state.expandedIds.delete(id);
          showToast('项目已删除');
        } else {
          await api(`/api/projects/${id}/${action}`, { method: 'POST' });
          showToast(action === 'start' ? '项目已启动' : '项目已停止');
        }
      } catch (error) {
        showToast(error.message, 'error');
      } finally {
        state.actionIds.delete(id);
        await refresh(true, true);
      }
    }

    addButton.addEventListener('click', beginAdd);
    compactButton.addEventListener('click', () => {
      state.compact = !state.compact;
      if (!state.compact) state.expandedIds.clear();
      saveCompactMode(state.compact);
      syncCompactMode();
      renderCurrentState();
    });
    document.querySelector('#project-filters').addEventListener('click', event => {
      const button = event.target.closest('[data-filter]');
      if (button) handleFilter(button);
    });
    content.addEventListener('click', event => {
      if (event.target.closest('.empty-add')) beginAdd();
      const action = event.target.closest('[data-action]');
      if (action) {
        handleAction(action);
        return;
      }
      if (state.compact && !event.target.closest('button')) {
        const head = event.target.closest('.project-head');
        const card = head && head.closest('.project-card');
        if (card) toggleCardExpand(card);
      }
    });
    content.addEventListener('pointerdown', event => {
      const handle = event.target.closest('.drag-handle');
      if (handle) {
        startDrag(event, handle);
        return;
      }
      state.selectingText = true;
    });
    window.addEventListener('pointerup', () => {
      state.selectingText = false;
    });
    form.addEventListener('submit', saveProject);
    document.querySelector('#close-dialog').addEventListener('click', () => dialog.close());
    document.querySelector('#cancel-dialog').addEventListener('click', () => dialog.close());
    dialog.addEventListener('close', () => {
      state.editingId = null;
    });
    document.addEventListener('visibilitychange', () => {
      syncPolling();
      if (!document.hidden) refresh(true, true);
    });

    syncCompactMode();
    refresh();
