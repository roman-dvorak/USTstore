import dayjs from "dayjs";

function getEffectiveValidUntil(contract) {
    let validUntil = dayjs(contract.valid_until);

    if (_.has(contract, "invalidation_date")) {
        const invalidationDate = dayjs(contract.invalidation_date).subtract(1, "days");
        validUntil = invalidationDate.isBefore(validUntil) ? invalidationDate : validUntil;
    }

    return validUntil
}

export function useContractUtilities() {
    return {
        getEffectiveValidUntil
    }
}