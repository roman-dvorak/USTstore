<template>
    <b-tbody :class="{inactive: !active}">
        <b-tr @click="$emit('change-open', contract._id)">
            <b-th>
                <div class="flex-space-between">
                    <div id="title">
                        {{contractTypeFormat(contract.type)}}
                        {{czechDateFormat(contract.valid_from)}} - {{czechDateFormat(contract.valid_until)}}
                        <span v-if="_.has(contract, 'invalidation_date')">
                            ({{czechDateFormat(contract.invalidation_date)}})
                        </span>
                    </div>
                    <b-button variant="secondary" size="sm" class="table-button">
                        <i class="material-icons">close</i>
                    </b-button>
                </div>
            </b-th>
        </b-tr>
        <b-tr v-if="open">
            <b-td class="details-wrapper">
                <b-table-simple>
                    <b-tbody>
                        <b-tr>
                            <b-td class="no-top-border">Druh smlouvy</b-td>
                            <b-td class="no-top-border">{{contractTypeFormat(contract.type)}}</b-td>
                        </b-tr>

                        <b-tr>
                            <td>Datum uzavření smlouvy</td>
                            <td>{{czechDateFormat(contract.signing_date)}}</td>
                        </b-tr>

                        <b-tr>
                            <td>Začátek platnosti</td>
                            <td>{{czechDateFormat(contract.valid_from)}}</td>
                        </b-tr>

                        <b-tr>
                            <td>Konec platnosti</td>
                            <td>{{czechDateFormat(contract.valid_until)}}</td>
                        </b-tr>

                        <b-tr v-if="_.has(contract, 'notes')">
                            <td>Poznámka</td>
                            <td>{{contract.notes}}</td>
                        </b-tr>

                        <b-tr>
                            <td>Sken podepsané smlouvy</td>
                            <td>
                                <div class="flex-space-between" v-if="_.has(contract, 'scan_signed_url')">
                                    <a :href="contract.scan_signed_url" target="_blank">Zobrazit</a>
                                    <b-button variant="secondary" size="sm" class="table-button">
                                        <i class="material-icons">edit</i>
                                    </b-button>
                                </div>
                                <a href="#" v-else>Nahrát</a>
                            </td>
                        </b-tr>

                        <b-tr v-if="_.has(contract, 'invalidation_date')">
                            <td>Zneplatněna ke dni</td>
                            <td>{{czechDateFormat(contract.invalidation_date)}}</td>
                        </b-tr>

                        <b-tr>
                            <td colspan="2" class="link-show-file">
                                <a :href="contract.url" target="_blank">
                                    Zobrazit smlouvu
                                </a>
                            </td>
                        </b-tr>

                    </b-tbody>
                </b-table-simple>
            </b-td>
        </b-tr>
    </b-tbody>
</template>

<script>
    import {useDateUtilities} from "../../utilities/date-utilities";

    export default {
        name: "Contract",
        setup() {
            return {
                ...useDateUtilities()
            }

        },
        props: {
            contract: Object,
            active: Boolean,
            open: Boolean,
            index: Number,
        },
        methods: {
            contractTypeFormat: function (type) {
                return {dpp: "Dohoda o provedení práce"}[type]
            }
        }
    }
</script>

<style scoped>
    * {
        text-align: left;
    }

    .details-wrapper {
        padding: 0 1rem;
    }

    .details-wrapper .table {
        margin-bottom: 0;
    }

    .no-top-border {
        border-top-width: 0;
    }

    .link-show-file {
        text-align: center;
    }

    .flex-space-between {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .table-button {
        padding-bottom: 0;
    }

    .table-button .material-icons {
        font-size: 17px;
    }

    .inactive {
        color: gray;
    }

    .inactive .table {
        color: gray;
    }
</style>