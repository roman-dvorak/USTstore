<template>
    <div>
        <h1>
            Attendance
        </h1>
        <attendance-calendar/>
    </div>
</template>

<script>
    import AttendanceCalendar from "../components/attendance-calendar/AttendanceCalendar";
    export default {
        name: "Attendance",
        components: {AttendanceCalendar}
    }
</script>

<style scoped>

</style>