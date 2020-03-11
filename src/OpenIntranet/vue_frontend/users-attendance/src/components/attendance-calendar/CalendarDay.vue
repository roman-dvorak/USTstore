<template>
    <div id="cell"
         :class="{'not-current': !currentMonth, selected: selected}"
         @click="$emit('date-change', date)">
        <div class="circle"
             :class="{
            'circle-hours': hours > 0,
            'circle-none': hours <= 0
        }">
            {{hours}}
        </div>
        <div id="day">
            {{date.date()}}
        </div>
    </div>

</template>

<script>
    export default {
        name: "CalendarDay",
        props: {
            date: Object,
            hours: Number,
            currentMonth: Boolean,
            selected: Boolean,
        }
    }
</script>

<style scoped>

    #cell {
        position: relative;
        display: block;
        height: 3rem;
        user-select: none;
        cursor: pointer;
    }

    .selected {
        background: #ddd;
    }

    .circle {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);

        border-radius: 17px;
        width: 34px;
        height: 34px;

        display: block;
        padding-top: 5px;
        font-weight: bold;
    }

    .circle-hours {
        background: var(--dark);
        color: white;
    }

    .circle-none {
        display: none;
    }

    #day {
        position: absolute;
        top: 1px;
        right: 1px;
        font-size: 0.8rem;
        font-weight: bold;
    }

    .not-current {
        opacity: 50%;
    }
</style>