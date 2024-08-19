import axios from 'axios';

const api = axios.create({
  baseURL: process.env.VUE_APP_BACKEND_URL || 'http://localhost:3000', // Default to localhost if not set
});

export default {
  login(token) {
    return api.post('/token', { token });
  },
  createUser(userData) {
    return api.post('/users/', userData);
  },
  getFeeds() {
    return api.get('/feeds/');
  },
  getFeed(feedName) {
    return api.get(`/feeds/${feedName}`);
  },
  createFeed(feedData) {
    return api.post('/feeds/', feedData);
  },
  deleteFeed(feedName) {
    return api.delete(`/feeds/${feedName}`);
  },
  updateFilters(feedName, filters) {
    return api.post(`/feeds/${feedName}/filters`, filters);
  },
  deleteFilters(feedName) {
    return api.delete(`/feeds/${feedName}/filters`);
  },
  addParent(feedName, parentData) {
    return api.post(`/feeds/${feedName}/parent`, parentData);
  },
  removeParent(feedName) {
    return api.delete(`/feeds/${feedName}/parent`);
  },
  getFeedRss(feedName) {
    return api.get(`/feeds/${feedName}/rss`);
  },
  getFeedJson(feedName) {
    return api.get(`/feeds/${feedName}/json`);
  },
  updateFeeds() {
    return api.post('/update-feeds/');
  }
};
