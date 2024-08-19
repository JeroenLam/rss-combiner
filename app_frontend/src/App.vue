<template>
  <div id="app">
    <header>
      <h1>Linux News Aggregator</h1>
    </header>
    <FeedList />
  </div>
</template>

<script>
import FeedList from './components/FeedList.vue';

export default {
  name: 'App',
  components: {
    FeedList
  }
};
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}

header {
  background-color: #333;
  color: white;
  padding: 1rem;
  text-align: center;
  margin-bottom: 2rem;
}
</style>
