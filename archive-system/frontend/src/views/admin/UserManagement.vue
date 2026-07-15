<template>
  <div class="page">
    <div class="page-head"><h2>用户管理</h2><button class="btn-primary" @click="showCreate=true">新建用户</button></div>
    <div class="card">
      <table class="data-table">
        <thead><tr><th>用户名</th><th>姓名</th><th>所属部门</th><th>角色</th><th style="width:80px">状态</th><th style="width:140px">操作</th></tr></thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td class="mono">{{ u.username }}</td><td>{{ u.name }}</td><td>{{ u.department }}</td><td>{{ roleLabel(u.role) }}</td>
            <td><span class="risk-tag" :class="u.is_active?'risk-tag--low':'risk-tag--high'">{{ u.is_active?'正常':'停用' }}</span></td>
            <td><button class="btn-sm">编辑</button><button class="btn-sm" style="margin-left:4px;color:var(--c-danger)">停用</button></td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="showCreate" class="modal-overlay" @click.self="showCreate=false"><div class="modal-card"><div class="modal-head"><h3>新建用户</h3><button class="modal-close" @click="showCreate=false"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button></div><div class="modal-body"><div class="form-group"><label>用户名</label><input class="field-input" /></div><div class="form-group"><label>姓名</label><input class="field-input" /></div><div class="form-group"><label>角色</label><select class="field-input"><option>系统管理员</option><option>档案管理员</option><option>审核员</option></select></div><div class="form-group"><label>初始密码</label><input class="field-input" type="password" /></div><div style="display:flex;gap:12px;justify-content:flex-end;margin-top:20px"><button class="btn-sm" @click="showCreate=false">取消</button><button class="btn-primary" @click="showCreate=false">确定</button></div></div></div></div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
const users = ref<any[]>([])
const showCreate = ref(false)
function roleLabel(r: string) { return { system_admin:'系统管理员',archive_admin:'档案管理员',reviewer:'审核员' }[r]||r }
</script>

<style scoped>
.page{max-width:var(--page-max);margin:0 auto}.page-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}.page-head h2{font-size:var(--fs-xl);font-weight:var(--fw-semibold);margin:0}.btn-primary{height:36px;padding:0 20px;border-radius:var(--r-sm);border:none;background:var(--c-accent);color:#fff;font-size:var(--fs-sm);font-weight:var(--fw-semibold);cursor:pointer}.btn-primary:hover{background:var(--c-accent-hover)}.card{background:var(--c-surface);border-radius:var(--r-lg);border:1px solid var(--c-border);overflow:hidden}.data-table{width:100%;border-collapse:collapse}.data-table th{padding:12px 16px;text-align:left;font-size:var(--fs-xs);font-weight:var(--fw-semibold);color:var(--c-text-muted);text-transform:uppercase;letter-spacing:0.5px;background:var(--c-bg);border-bottom:1px solid var(--c-border)}.data-table td{padding:12px 16px;font-size:var(--fs-sm);color:var(--c-text);border-bottom:1px solid var(--c-border-light)}.mono{font-family:'SF Mono','Fira Code',monospace;font-size:var(--fs-xs)}.btn-sm{height:30px;padding:0 14px;border-radius:var(--r-sm);border:1px solid var(--c-border);background:var(--c-surface);color:var(--c-text-secondary);font-size:var(--fs-xs);cursor:pointer}.btn-sm:hover{border-color:var(--c-accent);color:var(--c-accent)}.risk-tag{padding:2px 10px;border-radius:var(--r-full);font-size:11px;font-weight:var(--fw-bold)}.risk-tag--low{background:#F0FDF4;color:var(--c-success)}.risk-tag--high{background:#FEF2F2;color:var(--c-danger)}.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;z-index:100;backdrop-filter:blur(4px)}.modal-card{width:480px;background:var(--c-surface);border-radius:var(--r-lg);box-shadow:var(--s-dropdown)}.modal-head{display:flex;align-items:center;justify-content:space-between;padding:20px 24px;border-bottom:1px solid var(--c-border-light)}.modal-head h3{margin:0;font-size:var(--fs-lg)}.modal-close{width:32px;height:32px;border-radius:var(--r-sm);border:none;background:transparent;cursor:pointer;display:flex;align-items:center;justify-content:center;color:var(--c-text-muted)}.modal-close:hover{background:var(--c-bg)}.modal-body{padding:24px}.form-group{margin-bottom:16px}.form-group label{display:block;font-size:var(--fs-xs);font-weight:var(--fw-semibold);color:var(--c-text-muted);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px}.field-input{height:40px;padding:0 12px;border:1px solid var(--c-border);border-radius:var(--r-sm);font-size:var(--fs-base);background:var(--c-bg);outline:none;font-family:var(--font);width:100%}.field-input:focus{border-color:var(--c-accent)}
</style>
