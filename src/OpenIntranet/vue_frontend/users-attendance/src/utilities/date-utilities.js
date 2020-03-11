import dayjs from "dayjs";
import "dayjs/locale/cs"

function czechDateFormat(date) {
    return dayjs(date).locale("cs").format("l");
}

export function useDateUtilities() {
    return {
        czechDateFormat
    }
}
