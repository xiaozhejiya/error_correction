import { reactive, ref } from 'vue'

/**
 * useSelectableList — 列表多选模式 composable
 * @param {Object} options
 * @param {string} options.idKey - 项目 ID 字段名，默认 'id'
 * @returns {{ selectMode, selectedIds, toggleSelectMode, toggleSelect, selectAllItems, clearSelection }}
 */
export function useSelectableList({ idKey = 'id' } = {}) {
  const selectMode = ref(false)
  const selectedIds = reactive(new Set())

  const toggleSelectMode = () => {
    selectMode.value = !selectMode.value
    if (!selectMode.value) selectedIds.clear()
  }

  const toggleSelect = (id) => {
    selectedIds.has(id) ? selectedIds.delete(id) : selectedIds.add(id)
  }

  const selectAllItems = (items) => {
    items.forEach((item) => selectedIds.add(item[idKey]))
  }

  const clearSelection = () => {
    selectedIds.clear()
  }

  return {
    selectMode,
    selectedIds,
    toggleSelectMode,
    toggleSelect,
    selectAllItems,
    clearSelection,
  }
}
