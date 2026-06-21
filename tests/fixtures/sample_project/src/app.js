const express = require('express');

class Router {
  constructor() {
    this.routes = [];
  }

  get(path, handler) {
    this.routes.push({ method: 'GET', path, handler });
  }

  post(path, handler) {
    this.routes.push({ method: 'POST', path, handler });
  }
}

function createApp() {
  const router = new Router();
  router.get('/health', healthCheck);
  return router;
}

function healthCheck(req, res) {
  return { status: 'ok' };
}

module.exports = { createApp, Router };
