<template>
    <b-table-simple>
        <b-thead head-variant="dark">
            <b-tr>
                <b-th>
                    <div id="header">
                        <div>Smlouvy</div>
                        <b-button variant="light">Přidat</b-button>
                    </div>
                </b-th>
            </b-tr>
        </b-thead>
        <contract v-for="(contract, index) in contracts"
                  v-if="index < howManyVisible"
                  :contract="contract"
                  :active="index === whichActive"
                  :open="index === whichOpen"
                  :index="index"
        @change-open="newIndex => whichOpen = newIndex"/>
        <b-tbody v-if="howManyVisible < contracts.length">
            <b-tr @click="howManyVisible += 3">
                <b-th>
                    Zobrazit starší
                </b-th>
            </b-tr>
        </b-tbody>
    </b-table-simple>
</template>

<script>
    import Contract from "./Contract";
    import dayjs from "dayjs";

    export default {
        name: "ContractTable",
        components: {Contract},
        created() {
            this.prepareContracts()
        },
        data: function () {
            return {
                whichActive: 0,
                whichOpen: 0,
                howManyVisible: 1,
                contracts: []
            }
        },
        methods: {
            prepareContracts: function () {
                this.contracts = [
                    {
                        "_id": "2",
                        type: "dpp",
                        signing_date: "2020-06-01",
                        signing_place: "V Praze",
                        valid_from: "2020-06-01",
                        valid_until: "2020-12-31",
                        hour_rate: 100,
                        url: "#",
                    },
                    {
                        "_id": "1",
                        type: "dpp",
                        signing_date: "2020-01-01",
                        signing_place: "V Praze",
                        valid_from: "2020-01-01",
                        valid_until: "2020-12-31",
                        hour_rate: 100,
                        url: "#",
                        scan_signed_url: "#",
                        invalidation_date: "2020-05-05",
                        notes: "blabla"
                    },
                    {
                        "_id": "0",
                        type: "dpp",
                        signing_date: "2020-01-01",
                        signing_place: "V Praze",
                        valid_from: "2020-01-01",
                        valid_until: "2020-05-31",
                        hour_rate: 100,
                        url: "#",
                        scan_signed_url: "#",
                        invalidation_date: "2020-02-05",
                        notes: "blabla"
                    },
                ];

                this.whichOpen = this.whichActive = this.findActiveContractIndex(this.contracts);
                console.log("whichOpen", this.whichOpen);
                this.howManyVisible = this.whichOpen + 1;
            },
            findActiveContractIndex: function (contracts) {
                for (const [index, contract] of contracts.entries()) {
                    const today = dayjs().startOf("day");
                    const validFrom = dayjs(contract.valid_from);

                    let validUntil = dayjs(contract.valid_until);
                    if (this._.has(contract, "invalidation_date")) {
                        const invalidationDate = dayjs(contract.invalidation_date).subtract(1, "days");
                        validUntil = invalidationDate.isBefore(validUntil) ? invalidationDate : validUntil;
                    }

                    if (!(today.isBefore(validFrom) || today.isAfter(validUntil))) return index
                }

                return -1
            }
        },
        computed: {
            visibleContracts: function () {

            }
        }
    }
</script>

<style scoped>
    #header {
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
</style>