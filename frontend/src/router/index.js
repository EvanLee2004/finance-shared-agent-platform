import { createRouter, createWebHistory } from "vue-router";
import LoginView from "../views/LoginView.vue";
import HomeView from "../views/HomeView.vue";
import ChatView from "../views/ChatView.vue";
import SkillsView from "../views/SkillsView.vue";
import AdminView from "../views/AdminView.vue";
import { fetchMe } from "../api/client";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", name: "login", component: LoginView, meta: { public: true } },
    { path: "/", name: "home", component: HomeView },
    { path: "/chats", name: "chat", component: ChatView },
    { path: "/skills", name: "skills", component: SkillsView },
    { path: "/admin", name: "admin", component: AdminView },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

/** Soft session gate: unauthenticated users land on login without page flash of empty shells. */
router.beforeEach(async (to) => {
  if (to.meta.public) return true;
  try {
    await fetchMe();
    return true;
  } catch {
    return { name: "login", query: to.fullPath !== "/" ? { redirect: to.fullPath } : {} };
  }
});

export default router;
