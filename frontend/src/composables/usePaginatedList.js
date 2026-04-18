import { ref, computed, watch, onBeforeUnmount } from 'vue'

/**
 * usePaginatedList — 分页 + 筛选 + 防抖查询 composable
 * @param {Function} fetchFn - 查询函数 (params) => { items, total, total_pages? }
 * @param {Object} options
 * @param {number} options.pageSize - 每页条数，默认 10
 * @param {number} options.filterDebounce - 筛选防抖延迟（ms），默认 300
 * @param {number} options.keywordDebounce - 关键字防抖延迟（ms），默认 500
 */
export function usePaginatedList(fetchFn, { pageSize: defaultPageSize = 10, filterDebounce = 300, keywordDebounce = 500 } = {}) {
  const items = ref([])
  const page = ref(1)
  const pageSize = ref(defaultPageSize)
  const total = ref(0)
  const totalPages = computed(() => Math.ceil(total.value / pageSize.value))
  const loading = ref(false)

  let debounceTimer = null

  const doQuery = async (params = {}) => {
    loading.value = true
    try {
      const data = await fetchFn({ page: page.value, page_size: pageSize.value, ...params })
      items.value = data.items || []
      total.value = data.total || 0
      return data
    } finally {
      loading.value = false
    }
  }

  const goPage = (p) => {
    if (p < 1 || p > totalPages.value) return
    page.value = p
  }

  /**
   * 监听筛选变化，自动重置页码并防抖查询
   * @param {Function} source - watch source（返回筛选依赖数组）
   * @param {Function} buildParams - 构建查询参数
   * @param {Object} opts
   * @param {boolean} opts.isKeyword - 是否使用关键字防抖延迟
   * @param {Function} opts.afterQuery - 查询完成后的回调
   */
  const watchFilters = (source, buildParams, { isKeyword = false, afterQuery } = {}) => {
    const delay = isKeyword ? keywordDebounce : filterDebounce
    watch(source, () => {
      clearTimeout(debounceTimer)
      debounceTimer = setTimeout(async () => {
        page.value = 1
        const data = await doQuery(buildParams())
        afterQuery?.(data)
      }, delay)
    })
  }

  const watchPage = (buildParams, { afterQuery } = {}) => {
    watch(page, async () => {
      const data = await doQuery(buildParams())
      afterQuery?.(data)
    })
  }

  onBeforeUnmount(() => {
    if (debounceTimer) clearTimeout(debounceTimer)
  })

  return {
    items,
    page,
    pageSize,
    total,
    totalPages,
    loading,
    doQuery,
    goPage,
    watchFilters,
    watchPage,
  }
}
