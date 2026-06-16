import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import { createPinia } from "pinia";
import { createApp } from "vue";

import App from "./App.vue";
import router from "./router";
import "./styles/global.css";
import { installMojibakeGuard } from "./utils/mojibake";

const app = createApp(App);

app.use(createPinia());
app.use(router);
app.use(ElementPlus);
installMojibakeGuard(app);
app.mount("#app");
