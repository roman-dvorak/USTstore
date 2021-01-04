<template>
    <b-table-simple bordered>
        <b-thead head-variant="dark">
            <b-tr>
                <b-th colspan="7">
                    <div id="header">
                        <h4 id="month">{{date.format('MMMM')}} {{date.format('YYYY')}}</h4>
                        <b-button-group>
                            <b-button variant="light" @click="$emit('previous-month')">
                                Předchozí měsíc
                            </b-button>
                            <b-button variant="light" @click="$emit('next-month')">
                                Následující měsíc
                            </b-button>
                        </b-button-group>
                    </div>
                </b-th>
            </b-tr>
        </b-thead>
        <b-tbody>
            <b-tr>
                <b-th>Po</b-th>
                <b-th>Út</b-th>
                <b-th>St</b-th>
                <b-th>Čt</b-th>
                <b-th>Pá</b-th>
                <b-th>So</b-th>
                <b-th>Ne</b-th>
            </b-tr>
            <b-tr v-for="week in calendarMonth">
                <b-td v-for="day in week" id="day-cell">
                    <calendar-day :date="day.date"
                                  :hours="day.hours"
                                  :current-month="day.date.isSame(date, 'month')"
                                  :selected="day.date.isSame(date, 'day')"
                                  @date-change="newDate => $emit('date-change', newDate)"/>
                </b-td>
            </b-tr>
        </b-tbody>
    </b-table-simple>
</template>

<script>
    import CalendarDay from "./CalendarDay";
    import {buildCalendarMonth} from "./calendar";

    export default {
        name: "AttendanceCalendar",
        components: {CalendarDay},
        props: {
            date: Object,
            workspans: Object,
        },
        data: function () {
            return {}
        },
        computed: {
            calendarMonth: function () {
                return buildCalendarMonth(this.date, this.workspans)
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

    #month {
        margin-bottom: 0;
        text-transform: capitalize;
    }

    #day-cell {
        padding: 0;
    }
</style>