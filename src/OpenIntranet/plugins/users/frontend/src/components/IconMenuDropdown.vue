<template>
    <b-dropdown variant="link"
                size="sm"
                toggle-class="_cmi-dropdown-icon"
                no-caret
                v-bind="$props">
        <template v-slot:button-content>
            <i class="material-icons">menu</i>
        </template>
        <slot/>
        <b-dropdown-text v-if="!$slots.default" style="color: gray">
            {{emptyMessage}}
        </b-dropdown-text>
    </b-dropdown>
</template>

<script>
    export default {
        name: "IconMenuDropdown",
        props: {
            "disabled": Boolean,
            "dropup": Boolean,
            "dropright": Boolean,
            "dropleft": Boolean,
            "right": Boolean,
            "offset": [Number, String],
            "noFlip": Boolean,
            "boundary": [String, HTMLElement],
            "menuClass": [String, Array, Object],
            "lazy": Boolean,
            "emptyMessage": {
                type: String,
                default: "Není dostupná žádná akce"
            },
        },
    }
</script>

<style>

    ._cmi-dropdown-icon {
        color: var(--dark);
        padding: 0;
        height: 24px;
    }
</style>