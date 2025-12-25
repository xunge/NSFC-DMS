import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Query from '../views/Query.vue'
import ProjectDetail from '../views/ProjectDetail.vue'
import Manage from '../views/Manage.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/query',
    name: 'Query',
    component: Query
  },
  {
    path: '/project/:id',
    name: 'ProjectDetail',
    component: ProjectDetail,
    props: true
  },
  {
    path: '/manage',
    name: 'Manage',
    component: Manage
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
