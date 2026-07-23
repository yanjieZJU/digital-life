<template>
    <div>
        <div class="card">
            <div class="card-title">联想记忆概览</div>
            <el-row :gutter="20">
                <el-col :span="12">
                    <el-statistic title="记忆分块 (Chunks)" :value="assocData.chunks" />
                </el-col>
                <el-col :span="12">
                    <el-statistic title="关联数量 (Associations)" :value="assocData.associations" />
                </el-col>
            </el-row>
        </div>

        <el-row :gutter="20">
            <el-col :span="12">
                <div class="card">
                    <div class="card-title">热门关联 (Top Links)</div>
                    <el-table :data="assocData.top_links" style="width: 100%" size="small" empty-text="暂无热门关联">
                        <el-table-column prop="source_chunk_id" label="源分块" width="90" />
                        <el-table-column prop="target_chunk_id" label="目标分块" width="90" />
                        <el-table-column prop="weight" label="权重" width="80">
                            <template #default="scope">
                                <el-tag size="small">{{ scope.row.weight }}</el-tag>
                            </template>
                        </el-table-column>
                        <el-table-column prop="source_text" label="源内容" show-overflow-tooltip>
                            <template #default="scope">
                                <ContentActions
                                    :copy-text="scope.row.source_text"
                                    :fullscreen-text="scope.row.source_text"
                                    :fullscreen-title="`源分块 ${scope.row.source_chunk_id}`"
                                >
                                    <span class="chunk-cell">{{ scope.row.source_text }}</span>
                                </ContentActions>
                            </template>
                        </el-table-column>
                        <el-table-column prop="target_text" label="目标内容" show-overflow-tooltip>
                            <template #default="scope">
                                <ContentActions
                                    :copy-text="scope.row.target_text"
                                    :fullscreen-text="scope.row.target_text"
                                    :fullscreen-title="`目标分块 ${scope.row.target_chunk_id}`"
                                >
                                    <span class="chunk-cell">{{ scope.row.target_text }}</span>
                                </ContentActions>
                            </template>
                        </el-table-column>
                    </el-table>
                </div>
            </el-col>
            <el-col :span="12">
                <div class="card">
                    <div class="card-title">数据源 (Sources)</div>
                    <el-table :data="assocData.sources" style="width: 100%" size="small" height="400" empty-text="暂无数据源">
                        <el-table-column prop="source" label="来源" show-overflow-tooltip />
                        <el-table-column prop="count" label="分块数" width="100" />
                    </el-table>
                </div>
            </el-col>
        </el-row>
    </div>
</template>

<script setup>
import ContentActions from './ContentActions.vue'

defineProps({
    assocData: Object,
})
</script>

<style scoped>
.chunk-cell {
    display: block;
    max-width: 100%;
    overflow: hidden;
    padding-right: 52px;
    text-overflow: ellipsis;
    white-space: nowrap;
}
</style>
