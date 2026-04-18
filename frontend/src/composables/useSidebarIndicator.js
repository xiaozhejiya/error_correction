import { ref } from 'vue'

export function useSidebarIndicator() {
  const navRef = ref(null)
  const navBtnRefs = ref({})
  const indicatorStyle = ref({ opacity: 0, top: '0px', height: '0px' })
  const indicatorTransition = ref(true)

  const chatListRef = ref(null)
  const chatBtnRefs = ref({})
  const chatIndicatorStyle = ref({ opacity: 0, top: '0px', height: '0px' })
  const chatIndicatorTransition = ref(true)

  function updateIndicator(currentView, activeAiChatId, NAV_GROUPS, collapsedGroups, animate = true) {
    const cv = currentView
    const isChat = cv === 'ai-chat'

    // === 导航组指示器 ===
    if (isChat) {
      indicatorTransition.value = animate
      indicatorStyle.value = { opacity: 0, top: '0px', height: '0px' }
    } else {
      let matchId = null
      let matchGroupIdx = -1
      for (let gi = 0; gi < NAV_GROUPS.length; gi++) {
        for (const item of NAV_GROUPS[gi].items) {
          if (item.match && item.match(cv)) { matchId = item.id; matchGroupIdx = gi; break }
        }
        if (matchId) break
      }
      if (matchGroupIdx >= 0 && collapsedGroups[matchGroupIdx]) {
        indicatorTransition.value = false
        indicatorStyle.value = { opacity: 0, top: '0px', height: '0px' }
      } else if (!matchId || !navBtnRefs.value[matchId] || !navRef.value) {
        indicatorTransition.value = animate
        indicatorStyle.value = { opacity: 0, top: '0px', height: '0px' }
      } else {
        indicatorTransition.value = animate
        const navRect = navRef.value.getBoundingClientRect()
        const btnRect = navBtnRefs.value[matchId].getBoundingClientRect()
        indicatorStyle.value = {
          opacity: 1,
          top: (btnRect.top - navRect.top) + 'px',
          height: btnRect.height + 'px',
        }
      }
    }

    // === 对话区指示器 ===
    if (!isChat || !activeAiChatId) {
      chatIndicatorTransition.value = animate
      chatIndicatorStyle.value = { opacity: 0, top: '0px', height: '0px' }
    } else {
      const btnEl = chatBtnRefs.value[activeAiChatId]
      if (!btnEl || !chatListRef.value) {
        chatIndicatorTransition.value = animate
        chatIndicatorStyle.value = { opacity: 0, top: '0px', height: '0px' }
      } else {
        chatIndicatorTransition.value = animate
        const listRect = chatListRef.value.getBoundingClientRect()
        const btnRect = btnEl.getBoundingClientRect()
        chatIndicatorStyle.value = {
          opacity: 1,
          top: (btnRect.top - listRect.top) + 'px',
          height: btnRect.height + 'px',
        }
      }
    }
  }

  return {
    navRef, navBtnRefs, indicatorStyle, indicatorTransition,
    chatListRef, chatBtnRefs, chatIndicatorStyle, chatIndicatorTransition,
    updateIndicator,
  }
}
