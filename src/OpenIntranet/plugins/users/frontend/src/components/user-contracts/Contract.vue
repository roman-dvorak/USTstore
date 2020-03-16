<template>
    <b-tbody :class="{inactive: !active, invalidated: isInvalidated}">
        <b-tr>
            <b-th>
                <div class="flex-space-between">
                    <div id="title" @click="$emit('change-open', contract._id)">
                        {{contractTypeFormat(contract.type)}}
                        {{czechDateFormat(contract.valid_from)}} -
                        <span class="valid-until-date">{{czechDateFormat(contract.valid_until)}}</span>
                        <span v-if="isInvalidated">
                            {{czechDateFormat(contract.invalidation_date)}}
                        </span>
                    </div>
                    <icon-menu-dropdown right>
                        <b-dropdown-item-button v-if="hasAddSignedMenuItem">
                            Přidat sken podepsané smlouvy
                        </b-dropdown-item-button>
                        <b-dropdown-item-button v-if="hasDeleteMenuItem">
                            Smazat smlouvu
                        </b-dropdown-item-button>
                        <b-dropdown-item-button v-if="hasInvalidateMenuItem">
                            Zneplatnit smlouvu
                        </b-dropdown-item-button>
                        <b-dropdown-item-button v-if="hasChangeInvalidationDateMenuItem">
                            Změnit datum zneplatnění
                        </b-dropdown-item-button>
                    </icon-menu-dropdown>
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

                        <b-tr v-if="_.has(contract, 'scan_signed_url')">
                            <td>Sken podepsané smlouvy</td>
                            <td>
                                <a :href="contract.scan_signed_url"
                                   target="_blank">Zobrazit</a>
                            </td>
                        </b-tr>

                        <b-tr v-if="isInvalidated">
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
    import IconMenuDropdown from "../IconMenuDropdown";
    import {useContractUtilities} from "../../utilities/contract-utilities";
    import dayjs from "dayjs";

    export default {
        name: "Contract",
        components: {IconMenuDropdown},
        setup() {
            return {
                ...useDateUtilities(),
                ...useContractUtilities(),
            }

        },
        props: {
            contract: Object,
            active: Boolean,
            open: Boolean,
            invalidatable: Boolean,
        },
        methods: {
            contractTypeFormat: function (type) {
                return {dpp: "Dohoda o provedení práce"}[type]
            }
        },
        computed: {
            hasAddSignedMenuItem: function () {
                const effectiveValidUntil = this.getEffectiveValidUntil(this.contract);

                return dayjs().isBefore(effectiveValidUntil)
            },
            hasDeleteMenuItem: function () {
                return dayjs().isBefore(this.contract.valid_from)
            },
            hasInvalidateMenuItem: function () {
                return !this.hasChangeInvalidationDateMenuItem
            },
            hasChangeInvalidationDateMenuItem: function () {
                return _.has(this.contract, "invalidation_date")
            },
            isInvalidated: function () {
                return Boolean(this.contract.invalidation_date)
            }
        }
    }
</script>

<style scoped>
    * {
        text-align: left;
    }

    #title {
        cursor: pointer;
        user-select: none;
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

    .menu-icon {
        cursor: pointer;
    }

    .inactive {
        color: gray;
    }

    .inactive .table {
        color: gray;
    }

    .invalidated .valid-until-date {
        text-decoration: line-through;
    }
</style>