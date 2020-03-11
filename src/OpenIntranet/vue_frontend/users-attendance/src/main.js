import '@babel/polyfill'
import 'mutationobserver-shim'
import Vue from 'vue'

import './plugins/composition-api'
import './plugins/bootstrap-vue'
import './plugins/vue-tabulator'
import './plugins/vue-lodash'

import App from './App.vue'
import router from './router'

import dayjs from 'dayjs';
import 'dayjs/locale/cs'
import LocalizedFormat from 'dayjs/plugin/localizedFormat'

dayjs.locale('cs');
dayjs.extend(LocalizedFormat);

Vue.config.productionTip = false;

new Vue({
    router,
    render: h => h(App)
}).$mount('#app');
