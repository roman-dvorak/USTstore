<template>
    <b-table-simple>
        <b-thead head-variant="dark">
            <b-tr>
                <b-th>
                    <div class="flex-space-between">
                        <div>Smlouvy</div>
                        <b-button variant="light">Přidat</b-button>
                    </div>
                </b-th>
            </b-tr>
        </b-thead>
        <contract v-for="contract in visibleContracts"
                  :contract="contract"
                  :active="contract._id === whichActive"
                  :open="contract._id === whichOpen"
                  :invalidatable="isInvalidatable(contract)"
                  @change-open="newId => whichOpen = newId"/>
        <b-tbody v-if="contracts.length !== minVisible">
            <b-tr>
                <b-td>
                    <b-button-group>
                        <b-button variant="light"
                                  :disabled="minVisible + additionalVisible >= contracts.length"
                                  @click="additionalVisible += 3">
                            Zobrazit starší
                        </b-button>
                        <b-button variant="light"
                                  :disabled="additionalVisible === 0"
                                  @click="additionalVisible = 0">
                            Zobrazit méně
                        </b-button>
                    </b-button-group>
                </b-td>
            </b-tr>
        </b-tbody>
    </b-table-simple>
</template>

<script>
    import Contract from "./Contract";
    import dayjs from "dayjs";
    import {useContractUtilities} from "../../utilities/contract-utilities";

    export default {
        name: "ContractTable",
        setup() {
            return {
                ...useContractUtilities()
            }
        },
        components: {Contract},
        created() {
            this.getContracts()
        },
        data: function () {
            return {
                whichActive: null,
                whichOpen: 0,
                additionalVisible: 0,
                contracts: []
            }
        },
        methods: {
            getContracts: function () {
                // this.contracts = [
                //     {
                //         "_id": "2",
                //         type: "dpp",
                //         signing_date: "2020-06-01",
                //         signing_place: "V Praze",
                //         valid_from: "2020-06-01",
                //         valid_until: "2020-12-31",
                //         hour_rate: 100,
                //         url: "#",
                //     },
                //     {
                //         "_id": "1",
                //         type: "dpp",
                //         signing_date: "2020-01-01",
                //         signing_place: "V Praze",
                //         valid_from: "2020-01-01",
                //         valid_until: "2020-12-31",
                //         hour_rate: 100,
                //         url: "#",
                //         scan_signed_url: "#",
                //         invalidation_date: "2020-05-05",
                //         notes: "blabla"
                //     },
                //     {
                //         "_id": "0",
                //         type: "dpp",
                //         signing_date: "2020-01-01",
                //         signing_place: "V Praze",
                //         valid_from: "2020-01-01",
                //         valid_until: "2020-05-31",
                //         hour_rate: 100,
                //         url: "#",
                //         scan_signed_url: "#",
                //         invalidation_date: "2020-02-05",
                //         notes: "blabla"
                //     },
                // ];

                this.whichOpen = this.whichActive = this.findActiveContractId(this.contracts);
            },
            findActiveContractId: function (contracts) {
                for (const contract of contracts) {
                    const today = dayjs().startOf("day");
                    const validFrom = dayjs(contract.valid_from);

                    const validUntil = this.getEffectiveValidUntil(contract);

                    if (!(today.isBefore(validFrom) || today.isAfter(validUntil))) return contract._id
                }

                return null
            },
            isInvalidatable: function (contract) {
                return !dayjs().startOf("day").isAfter(dayjs(contract.valid_until))
            }
        },
        computed: {
            visibleContracts: function () {
                return this.contracts.slice(0, this.minVisible + this.additionalVisible)
            },
            minVisible: function () {
                return Math.max(1, this.contracts.findIndex(c => c._id === this.whichActive) + 1);
            }
        }
    }
</script>

<style scoped>
    .flex-space-between {
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
</style>