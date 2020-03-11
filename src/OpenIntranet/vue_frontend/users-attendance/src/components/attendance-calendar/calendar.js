export function buildCalendarMonth(date, workspans) {
    const month = date.startOf("month");

    const firstDayNumber = (month.day() + 6) % 7;
    const firstCellDate = month.subtract(firstDayNumber, "days");

    const monthArray = [];

    for (let week = 0; week < 6; week++) {
        const weekArray = [];

        for (let weekDay = 0; weekDay < 7; weekDay++) {
            const cellDate = firstCellDate.add(week * 7 + weekDay, "days");
            const cellDateIso = cellDate.format("YYYY-MM-DD");

            let hours = 0;
            if (workspans.hasOwnProperty(cellDateIso)) {
                hours = workspans[cellDateIso].reduce((sum, ws) => sum + ws.hours, 0)
            }

            weekArray.push({
                "date": cellDate,
                "hours": hours,
            })
        }

        monthArray.push(weekArray);
    }

    return monthArray
}


