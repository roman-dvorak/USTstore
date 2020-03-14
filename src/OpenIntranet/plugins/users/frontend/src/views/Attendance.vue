<template>
    <b-container>
        <b-row>
            <b-col>
                <h1>
                    Attendance
                </h1>
            </b-col>
        </b-row>
        <b-row>
            <b-col cols="6">
                <attendance-calendar :date="date"
                                     :workspans="workspans"
                                     @previous-month="previousMonth"
                                     @next-month="nextMonth"
                                     @date-change="dateChanged"/>
            </b-col>
        </b-row>
    </b-container>
</template>

<script>
    import AttendanceCalendar from "../components/attendance-calendar/AttendanceCalendar";
    import dayjs from "dayjs";

    export default {
        name: "Attendance",
        components: {AttendanceCalendar},
        data: function () {
            return {
                workspans: {
                    "2020-03-05": [{"hours": 5}, {"hours": 2.5}]
                },
                date: null
            }
        },
        methods: {
            previousMonth: function () {
                this.date = this.date.startOf("month").subtract(1, "months");
            },
            nextMonth: function () {
                this.date = this.date.startOf("month").add(1, "months");
            },
            dateChanged: function (newDate) {
                this.date = newDate
            }
        },
        created() {
            const dateQuery = this.$route.query.date;
            if (dateQuery) {
                this.date = dayjs(dateQuery)
            } else {
                this.date = dayjs().startOf("day")
            }
        }
    }
</script>

<style scoped>

</style>