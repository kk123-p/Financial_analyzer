// router.js — Hash-based SPA router
import { $, $$ } from './utils.js';

export class Router {
  constructor(routes) {
    this.routes = routes; // { pattern: handler(viewName, params) }
    this.currentView = null;
    this.currentParams = {};
  }

  start() {
    window.addEventListener('hashchange', () => this._handleRoute());
    if (!location.hash) {
      location.hash = '#/dashboard';
    } else {
      this._handleRoute();
    }
  }

  navigate(hash) {
    location.hash = hash;
  }

  getCurrentRoute() {
    return { view: this.currentView, params: this.currentParams };
  }

  _handleRoute() {
    const hash = location.hash.slice(1) || '/dashboard';
    const [path, ...rest] = hash.split('/').filter(Boolean);

    let matched = false;
    for (const [pattern, handler] of Object.entries(this.routes)) {
      const patternParts = pattern.split('/').filter(Boolean);
      const hashParts = hash.slice(1).split('/').filter(Boolean);

      if (patternParts.length !== hashParts.length) continue;

      const params = {};
      let matches = true;
      for (let i = 0; i < patternParts.length; i++) {
        if (patternParts[i].startsWith(':')) {
          params[patternParts[i].slice(1)] = hashParts[i];
        } else if (patternParts[i] !== hashParts[i]) {
          matches = false;
          break;
        }
      }

      if (matches) {
        this.currentView = handler;
        this.currentParams = params;
        this._activateView(handler, params);
        matched = true;
        break;
      }
    }

    if (!matched) {
      this.navigate('/dashboard');
      return;
    }

    const activeTab = this.currentView.split('/')[0];
    $$('.nav-tab').forEach(tab => {
      const route = tab.dataset.route;
      tab.classList.toggle('active', route === '/' + activeTab);
    });
  }

  _activateView(viewName, params) {
    $$('.view').forEach(v => v.classList.remove('active'));

    const viewId = 'view-' + viewName.split('/')[0];
    const view = document.getElementById(viewId);
    if (view) {
      view.classList.add('active');
    }

    window.dispatchEvent(new CustomEvent('viewchange', {
      detail: { view: viewName, params }
    }));
  }

  getViewName() {
    const hash = location.hash.slice(1) || '/dashboard';
    const parts = hash.split('/').filter(Boolean);
    return parts[0] || 'dashboard';
  }

  getModuleKey() {
    const hash = location.hash.slice(1) || '';
    const parts = hash.split('/').filter(Boolean);
    return parts[1] || null;
  }
}
