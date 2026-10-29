/**
 * AeroGuard — Main Entry Point
 * Inicializa el router y registra todas las vistas.
 */

import { Router } from './app.js';
import { LoginView, ResetPasswordView } from './views/login.view.js';
import { DashboardView }      from './views/dashboard.view.js';
import { DetectionsView }     from './views/detections.view.js';
import { AlertsView }         from './views/alerts.view.js';
import { ZonesView }          from './views/zones.view.js';
import { UsersView }          from './views/users.view.js';
import { SensorsView }        from './views/sensors.view.js';
import {
  ReportsView,
  HistoryView,
  AuditView,
  DetectionConfigView,
  TrajectoryView,
} from './views/misc.views.js';

// Initialize router
const router = new Router();

router
  .register('#/login',            () => new LoginView())
  .register('#/reset-password',    () => new ResetPasswordView())
  .register('#/dashboard',        () => new DashboardView(),       ['admin', 'operator', 'analyst'])
  .register('#/detections',       () => new DetectionsView(),      ['admin', 'operator', 'analyst'])
  .register('#/alerts',           () => new AlertsView(),          ['admin', 'operator', 'analyst'])
  .register('#/zones',            () => new ZonesView(),           ['admin', 'operator', 'analyst'])
  .register('#/users',            () => new UsersView(),           ['admin'])
  .register('#/sensors',          () => new SensorsView(),         ['admin'])
  .register('#/reports',          () => new ReportsView(),         ['admin', 'analyst'])
  .register('#/history',          () => new HistoryView(),         ['admin', 'operator', 'analyst'])
  .register('#/audit',            () => new AuditView(),           ['admin', 'analyst'])
  .register('#/detection-config', () => new DetectionConfigView(), ['admin'])
  .register('#/trajectory',       () => new TrajectoryView(),      ['admin', 'operator', 'analyst']);

// Start the SPA
router.start();

console.log('AeroGuard — monitoreo experimental. Consultar /health para identificar la versión del backend.');
