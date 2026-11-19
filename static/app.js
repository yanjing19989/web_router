    const icons = {
      play: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 5v14l11-7L8 5Z"/></svg>',
      stop: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="6" width="12" height="12" rx="1"/></svg>',
      open: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 4h6v6m0-6-9 9"/><path d="M19 13v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h5"/></svg>',
      folder: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/><path d="M3 9h18"/></svg>',
      edit: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m14 5 5 5M4 20l3.5-.7L19 7.8a2.1 2.1 0 0 0-3-3L4.7 16.3 4 20Z"/></svg>',
      trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 7h16M9 7V4h6v3m3 0-1 13H7L6 7m4 4v5m4-5v5"/></svg>'
    };

    const state = {
      projects: [],
      refreshing: false,
      loaded: false,
      hasRunningProjects: false,
      selectingText: false,
      editingId: null,
      actionIds: new Set(),
      filterTypes: new Set(['npm', 'python', 'static']),
      pollTimer: null
    };
    const content = document.querySelector('#project-content');
    const dialog = document.querySelector('#project-dialog');
    const form = document.querySelector('#project-form');
    const addButton = document.querySelector('#add-project');

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

    function updateCard(card, project) {
      const refs = card._refs;
      const running = project.status === 'running';
      const busy = state.actionIds.has(project.id);

      card.classList.toggle('running', running);
      setText(refs.name, project.name);
      setText(refs.type, project.type);
      setText(refs.port, `:${project.port}`);
      const portTitle = `端口 ${project.port}`;
      if (refs.port.title !== portTitle) refs.port.title = portTitle;

      const statusClass = `status ${project.status}`;
      if (refs.status.className !== statusClass) refs.status.className = statusClass;
      setText(refs.status, running ? '运行中' : '已停止');

      setText(refs.pid, project.pid ? String(project.pid) : '—', true);
      setText(refs.cpu, running ? `${project.cpu_percent.toFixed(1)}%` : '—', true);
      setText(refs.uss, running ? formatBytes(project.memory_uss_bytes) : '—', true);
      setText(refs.vms, running ? formatBytes(project.memory_vms_bytes) : '—', true);

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
      const title = document.createElement('div');
      title.className = 'project-title';
      const h3 = document.createElement('h3');
      const typeLine = document.createElement('div');
      typeLine.className = 'type-line';
      const type = document.createElement('span');
      type.className = 'type-badge';
      const port = document.createElement('span');
      port.className = 'port-badge';
      typeLine.append(type, port);
      title.append(h3, typeLine);
      const status = document.createElement('span');
      head.append(title, status);

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

      const actions = document.createElement('div');
      actions.className = 'project-actions';
      const primary = actionButton('启动', 'start', icons.play, 'button-primary');
      const open = actionButton('打开', 'open', icons.open);
      const folder = actionButton('打开所在目录', 'open-folder', icons.folder, 'icon-only', true);
      const edit = actionButton('编辑项目', 'edit', icons.edit, 'icon-only', true);
      const remove = actionButton('删除项目', 'delete', icons.trash, 'button-danger icon-only', true);
      actions.append(primary, open, folder, edit, remove);
      card.append(head, metrics, details, actions);

      card._refs = {
        name: h3,
        type,
        port,
        status,
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
        (!force && state.loaded && (document.hidden || !state.hasRunningProjects || hasActiveSelection()))
      ) return;
      state.refreshing = true;
      try {
        const payload = await api('/api/projects');
        if (force || !hasActiveSelection()) render(payload);
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
    document.querySelector('#project-filters').addEventListener('click', event => {
      const button = event.target.closest('[data-filter]');
      if (button) handleFilter(button);
    });
    content.addEventListener('click', event => {
      if (event.target.closest('.empty-add')) beginAdd();
      const action = event.target.closest('[data-action]');
      if (action) handleAction(action);
    });
    content.addEventListener('pointerdown', () => {
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

    refresh();
  
