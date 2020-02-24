<template>
    <div>

        <nav class="top_nav_base navbar navbar-toggleable-md navbar-inverse fixed-top bg-inverse">
            <a href="/">
                <img src="../assets/ust-logo.png" alt="Logo" class="logo">
            </a>

            <span>
                  <span class="current_cart"></span>
                <i class="material-icons">account_circle</i>user
                <a href="/logout">Odhlásit</a>
                <br> Sklad: Nic
                <a href="/login">přihlásit se</a>
                      <i class="material-icons barcode-icon">remove</i>
              </span>

        </nav>

    </div>
</template>

<script>
    export default {
        name: "HeaderBar"
    }
</script>

<style scoped>
    /*.material-icons {*/
    /*    font-family: 'Material Icons';*/
    /*    font-weight: normal;*/
    /*    font-style: normal;*/
    /*    font-size: 24px; !* Preferred icon size *!*/
    /*    display: inline-block;*/
    /*    line-height: 1;*/
    /*    text-transform: none;*/
    /*    letter-spacing: normal;*/
    /*    word-wrap: normal;*/
    /*    white-space: nowrap;*/
    /*    direction: ltr;*/

    /*    !* Support for all WebKit browsers. *!*/
    /*    -webkit-font-smoothing: antialiased;*/
    /*    !* Support for Safari and Chrome. *!*/
    /*    text-rendering: optimizeLegibility;*/

    /*    !* Support for Firefox. *!*/
    /*    -moz-osx-font-smoothing: grayscale;*/

    /*    !* Support for IE. *!*/
    /*    font-feature-settings: 'liga';*/
    /*}*/

    .card {
        margin-top: 15pt;
        margin-bottom: 15px;
    }

    .top_nav_base {
        background-color: white;
        width: 100%;
        height: 5em;
        border-bottom: black solid 2px;
    }

    .table_style {
        /*border: 1pt gray solid;*/
    }

    .logo {
        height: 4em;
        vertical-align: middle;
    }
</style>