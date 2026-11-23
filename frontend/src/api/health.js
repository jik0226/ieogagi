import { get } from './client.js';

// #27
export const getHealth = () => get('/health');
