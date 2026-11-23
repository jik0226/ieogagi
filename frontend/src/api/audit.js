import { get } from './client.js';

// #26 (empty filters are dropped from the query string)
export const listAuditLogs = ({ action, result, dateFrom, dateTo, limit = 50, offset = 0 } = {}) =>
  get('/audit-logs', {
    query: {
      action,
      result,
      date_from: dateFrom,
      date_to: dateTo,
      limit,
      offset,
    },
  });
