<template>
  <div class="page">
    <div class="page-head"><h2>数据同步</h2></div>
    <div class="sync-tabs">
      <button :class="['sync-tab',{active:tab==='file'}]" @click="tab='file'">文件同步</button>
      <button :class="['sync-tab',{active:tab==='db'}]" @click="tab='db'">数据库同步</button>
      <button :class="['sync-tab',{active:tab==='history'}]" @click="tab='history'">同步历史</button>
    </div>
    <div class="card" v-if="tab==='file'">
      <div class="card-body">
        <div class="form-group"><label>共享目录路径</label><input class="field-input" placeholder="FTP://或 SMB://路径" /></div>
        <div class="form-group"><label>同步频率</label><select class="field-input" style="width:200px"><option>每天</option><option>每周</option></select></div>
        <div style="display:flex;gap:8px"><button class="btn-primary">保存配置</button><button class="btn-sm">手动同步</button></div>
      </div>
    </div>
    <div class="card" v-else-if="tab==='db'">
      <div class="card-body">
        <div class="form-group"><label>主机地址</label><input class="field-input" /></div>
        <div class="form-group"><label>数据库名</label><input class="field-input" /></div>
        <div class="form-group"><label>只读账号</label><input class="field-input" /></div>
        <button class="btn-primary">保存配置</button>
      </div>
    </div>
    <div class="card" v-else>
      <table class="data-table"><thead><tr><th>开始时间</th><th>类型</th><th>状态</th><th>新增</th><th>更新</th><th>失败</th></tr></thead><tbody><tr><td colspan="6" class="table-empty">暂无同步记录</td></tr></tbody></table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
const tab = ref('file')
</script>

<style scoped>
.page{max-width:var(--page-max);margin:0 auto}.page-head{margin-bottom:20px}.page-head h2{font-size:var(--fs-xl);font-weight:var(--fw-semibold);margin:0}.sync-tabs{display:flex;gap:4px;margin-bottom:16px;background:var(--c-surface);border-radius:var(--r-md);padding:3px;width:fit-content;border:1px solid var(--c-border)}.sync-tab{padding:6px 16px;border-radius:var(--r-sm);border:none;background:transparent;color:var(--c-text-secondary);font-size:var(--fs-sm);font-weight:var(--fw-medium);cursor:pointer;transition:all var(--t-fast)}.sync-tab.active{background:var(--c-accent);color:#fff}.card{background:var(--c-surface);border-radius:var(--r-lg);border:1px solid var(--c-border);overflow:hidden}.card-body{padding:20px}.btn-primary{height:36px;padding:0 20px;border-radius:var(--r-sm);border:none;background:var(--c-accent);color:#fff;font-size:var(--fs-sm);font-weight:var(--fw-semibold);cursor:pointer}.btn-primary:hover{background:var(--c-accent-hover)}.btn-sm{height:36px;padding:0 16px;border-radius:var(--r-sm);border:1px solid var(--c-border);background:var(--c-surface);color:var(--c-text-secondary);font-size:var(--fs-sm);cursor:pointer}.btn-sm:hover{border-color:var(--c-accent);color:var(--c-accent)}.form-group{margin-bottom:16px}.form-group label{display:block;font-size:var(--fs-xs);font-weight:var(--fw-semibold);color:var(--c-text-muted);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px}.field-input{height:40px;padding:0 12px;border:1px solid var(--c-border);border-radius:var(--r-sm);font-size:var(--fs-base);background:var(--c-bg);outline:none;font-family:var(--font);width:100%;max-width:400px}.field-input:focus{border-color:var(--c-accent)}.data-table{width:100%;border-collapse:collapse}.data-table th{padding:12px 16px;text-align:left;font-size:var(--fs-xs);font-weight:var(--fw-semibold);color:var(--c-text-muted);text-transform:uppercase;letter-spacing:0.5px;background:var(--c-bg);border-bottom:1px solid var(--c-border)}.table-empty{padding:48px;text-align:center;color:var(--c-text-muted)}
</style>
