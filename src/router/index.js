import { createRouter, createWebHistory } from 'vue-router'
import Analysis from '../views/analysis.vue'
import Contact from '../views/contact.vue'
import Fact from '../views/fact.vue'
import LearnMore from '../views/learnmore.vue'

const routes = [
  {
    path: '/',
    redirect: '/analysis'
  },
  {
    path: '/analysis',
    name: 'Analysis',
    component: Analysis,
    meta: {
      title: '分类展示',
      icon: 'bi-bar-chart-line'
    }
  },
  {
    path: '/facts',
    name: 'Facts',
    component: Fact,
    meta: {
      title: '模型试验',
      icon: 'bi-lightbulb'
    }
  },
  {
    path: '/learn-more',
    name: 'LearnMore',
    component: LearnMore,
    meta: {
      title: '数据分析',
      icon: 'bi-book'
    }
  },
  {
    path: '/contact',
    name: 'Contact',
    component: Contact,
    meta: {
      title: '更多反思',
      icon: 'bi-envelope'
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router