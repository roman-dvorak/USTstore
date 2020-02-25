<template>
    <b-navbar class="top_nav_base" toggleable="true">
        <a href="/">
            <img src="../assets/ust-logo.png" alt="Logo" class="logo">
        </a>

        <span>
            <span v-if="currentUser">
                <span class="current_cart"/>
                <i class="material-icons">account_circle</i>{{currentUser.user}}
                <a href="/logout">Odhlásit</a>
                <br> Sklad:
                <span v-if="currentUser.param.warehouse_info">
                    {{currentUser.param.warehouse_info.name}}
                </span>
                <span v-else>
                    Nic
                </span>
            </span>
            <span v-else>
                <a href="/login">přihlásit se</a>
            </span>
            <i class="material-icons barcode-icon">remove</i>
        </span>
    </b-navbar>
</template>

<script>
    export default {
        name: "HeaderBar",
        props: ["currentUser"],
    }
</script>

<style scoped>
    .card {
        margin-top: 15pt;
        margin-bottom: 15px;
    }

    .top_nav_base {
        background-color: white;
        width: 100%;
        height: 5em;
        border-bottom: black solid 2px;
        /*display: flex;*/
        /*align-items: center;*/
        /*justify-content: space-between;*/
        /*padding: .5rem 1rem;*/
    }

    .table_style {
        /*border: 1pt gray solid;*/
    }

    .logo {
        height: 4em;
        vertical-align: middle;
    }
</style>