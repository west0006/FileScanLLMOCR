<template>
  <div class="page">
    <div class="page-head"><h2>角色权限</h2></div>
    <div class="card">
      <table class="data-table">
        <thead><tr><th>角色名称</th><th>描述</th><th style="width:80px">用户数</th><th style="width:120px">操作</th></tr></thead>
        <tbody>
          <tr v-for="r in roles" :key="r.id">
            <td class="font-medium">{{ r.name }}</td><td>{{ r.description }}</td><td>{{ r.user_count }}</td>
            <td><button class="btn-sm">权限配置</button></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
const roles = ref([{ id:1, name:'系统管理员', description:'全部权限', user_count:1 },{ id:2, name:'档案管理员', description:'档案管理与检索', user_count:2 },{ id:3, name:'审核员', description:'开放审核', user_count:5 }])
</script>

<style scoped>
.page{max-width:var(--page-max);margin:0 auto}.page-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}.page-head h2{font-size:var(--fs-xl);font-weight:var(--fw-semibold);margin:0}.card{background:var(--c-surface);border-radius:var(--r-lg);border:1px solid var(--c-border);overflow:hidden}.data-table{width:100%;border-collapse:collapse}.data-table th{padding:12px 16px;text-align:left;font-size:var(--fs-xs);font-weight:var(--fw-semibold);color:var(--c-text-muted);text-transform:uppercase;letter-spacing:0.5px;background:var(--c-bg);border-bottom:1px solid var(--c-border)}.data-table td{padding:12px 16px;font-size:var(--fs-sm);color:var(--c-text);border-bottom:1px solid var(--c-border-light)}.btn-sm{height:30px;padding:0 14px;border-radius:var(--r-sm);border:1px solid var(--c-border);background:var(--c-surface);color:var(--c-text-secondary);font-size:var(--fs-xs);cursor:pointer}.btn-sm:hover{border-color:var(--c-accent);color:var(--c-accent)}.font-medium{font-weight:var(--fw-medium)}
</style>
