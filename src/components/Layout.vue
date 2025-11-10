<template>
  <div class="layout-container">
    <!-- 侧边导航栏 -->
    <div class="sidebar sidebar-medical" :class="{ 'sidebar-collapsed': isCollapsed }">
      <div class="sidebar-header">
        <button 
          class="btn btn-link text-light sidebar-toggle"
          @click="toggleSidebar"
        >
          <i class="bi bi-list fs-3"></i>
        </button>
        <div class="d-flex align-items-center">
          <div class="brand-square me-2" v-if="!isCollapsed">
            <img :src="logo" alt="logo" class="brand-square-img" />
          </div>
          <h4 v-if="!isCollapsed" class="sidebar-title text-light">中国流行传染病抽省监视与可视化</h4>
        </div>
      </div>
      
      <ul class="nav nav-pills flex-column mb-auto">
        <li class="nav-item" v-for="route in routes" :key="route.path">
          <router-link 
            :to="route.path" 
            class="nav-link d-flex align-items-center"
            :class="{ 'active': $route.path === route.path }"
          >
            <i :class="route.meta.icon" class="nav-icon"></i>
            <span v-if="!isCollapsed" class="nav-text">{{ route.meta.title }}</span>
          </router-link>
        </li>
      </ul>
      
      <div class="sidebar-footer" v-if="!isCollapsed">
        <small class="text-muted">© 2025 疫情监测</small>
      </div>
    </div>
    
    <!-- 主内容区域 -->
    <div class="main-content">
      <div class="content-wrapper">
        <router-view></router-view>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const isCollapsed = ref(false)
import logo from '../assets/medical-cross.svg'

const routes = computed(() => 
  router.getRoutes()
    .filter(route => route.meta && route.meta.title)
    .sort((a, b) => {
      const order = ['/analysis', '/facts', '/learn-more', '/contact']
      return order.indexOf(a.path) - order.indexOf(b.path)
    })
)

const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value
}
</script>

<style scoped>
.layout-container {
  position: relative;
  width: 100vw;
  height: 100vh;
  margin: 0;
  padding: 0;
  overflow: hidden;
}

.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  width: 280px;
  height: 100vh;
  padding: 1rem;
  box-shadow: 2px 0 8px rgba(2,48,45,0.12);
  transition: width 0.3s ease, background 0.3s ease;
  z-index: 1000;
  overflow-y: auto;
  background: linear-gradient(180deg, #053b3a 0%, #0b6b67 100%);
}

.sidebar-collapsed {
  width: 80px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
.brand-square-img{ width:28px; height:28px; background: rgba(255,255,255,0.06); padding:4px; border-radius:6px }

.sidebar-toggle {
  border: none !important;
  padding: 0.5rem;
  margin-right: 1rem;
}

.sidebar-collapsed .sidebar-toggle {
  margin-right: 0;
}

.sidebar-title {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 600;
}

.nav-link {
  color: rgba(255,255,255,0.95) !important;
  padding: 0.75rem 1rem;
  margin-bottom: 0.5rem;
  border-radius: 0.5rem;
  transition: all 0.3s ease;
  text-decoration: none;
}

.nav-link:hover {
  background-color: rgba(255,255,255,0.1);
  color: white !important;
}

.nav-link.active {
  background-color: rgba(13,110,253,0.12) !important;
  color: #eafffb !important;
  box-shadow: inset 0 0 12px rgba(0,0,0,0.12);
}

.nav-icon {
  font-size: 1.2rem;
  width: 24px;
  text-align: center;
}

.nav-text {
  margin-left: 1rem;
  font-weight: 500;
}

.sidebar-collapsed .nav-text {
  display: none;
}

.sidebar-footer {
  margin-top: auto;
  padding-top: 1rem;
  border-top: 1px solid rgba(255,255,255,0.06);
  text-align: center;
}

.main-content {
  position: absolute;
  top: 0;
  left: 280px;
  width: calc(100vw - 280px);
  height: 100vh;
  background-color: #f8f9fa;
  transition: all 0.3s ease;
  overflow-y: auto;
}

.sidebar-collapsed ~ .main-content {
  left: 80px;
  width: calc(100vw - 80px);
}

.content-wrapper {
  padding: 2rem;
  min-height: calc(100vh - 4rem);
  width: 100%;
}

</style>