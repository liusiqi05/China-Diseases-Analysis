<template>
  <nav class="navbar navbar-expand-lg navbar-medical">
    <div class="container-fluid">
      <a class="navbar-brand d-flex align-items-center" href="#">
        <img :src="logo" alt="logo" class="brand-icon" />
        <span class="brand-text">疾病监测可视化面板</span>
      </a>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="navbarNav">
        <ul class="navbar-nav ms-auto">
          <li class="nav-item">
            <a class="nav-link" href="#">仪表盘</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="#">数据说明</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="#">帮助</a>
          </li>
        </ul>
      </div>
    </div>
  </nav>
</template>

<script>
import logo from '../assets/medical-cross.svg'

export default {
  name: 'Navbar',
  data() { return { logo } }
}
</script>

<style scoped>
.navbar-medical{
  background: linear-gradient(90deg, #0b6b67 0%, #0e9b8a 100%);
  color: #fff;
  box-shadow: 0 4px 14px rgba(2,48,45,0.25);
}
.navbar-medical .navbar-brand{ color: #fff !important; text-decoration: none }
.navbar-medical .brand-icon{ margin-right: 10px; background: rgba(255,255,255,0.06); padding:4px; border-radius:6px }
.navbar-medical .brand-text{ font-weight:600; margin-left:6px }
.navbar-medical .nav-link{ color: rgba(255,255,255,0.9) }
.navbar-medical .nav-link:hover{ color: #e8fff8 }

/* make navbar compact on small screens */
@media (max-width: 576px){
  .navbar-medical .brand-text{ display:none }
}
</style>
