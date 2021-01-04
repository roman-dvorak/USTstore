<template>
    <b-container>
        <b-row>
            <b-col>
                <h1>
                    Users
                </h1>
            </b-col>
        </b-row>
        <b-row>
            <b-col cols="6">
                <contract-table/>
            </b-col>
        </b-row>
    </b-container>
</template>

<script>
    import ContractTable from "../components/user-contracts/ContractTable";
    export default {
        name: "Users",
        components: {ContractTable}
    }
</script>

<style scoped>

</style>