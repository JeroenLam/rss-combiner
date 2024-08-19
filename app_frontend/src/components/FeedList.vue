<template>
  <div class="feed-list">
    <div v-for="(feed, index) in feeds" :key="index" class="feed-card">
      <h2>{{ feed.title }}</h2>
      <ul>
        <li v-for="(item, i) in feed.items" :key="i">
          <a :href="item.link">{{ item.title }}</a>
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
import api from '../services/api';

export default {
  data() {
    return {
      feeds: []
    };
  },
  created() {
    this.fetchFeeds();
  },
  methods: {
    async fetchFeeds() {
      try {
        const response = await api.getFeeds();
        this.feeds = response.data;
      } catch (error) {
        console.error('Failed to fetch feeds:', error);
      }
    }
  }
};
</script>

<style scoped>
.feed-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
  padding: 1rem;
}

.feed-card {
  border: 1px solid #ccc;
  padding: 1rem;
  border-radius: 4px;
  background-color: #f9f9f9;
}

.feed-card h2 {
  margin-top: 0;
}

.feed-card ul {
  list-style: none;
  padding: 0;
}

.feed-card li {
  margin: 0.5rem 0;
}

.feed-card a {
  color: #333;
  text-decoration: none;
}

.feed-card a:hover {
  text-decoration: underline;
}
</style>
