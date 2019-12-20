function validateOneDateBeforeOther(soonerInput, laterInput) {
    let soonerVal = $(soonerInput).val();
    let laterVal = $(laterInput).val();
    console.log(soonerVal);

    if (soonerVal === "" || laterVal === "") return false;

    if (moment(soonerVal).isAfter(moment(laterVal))) {
        markInvalid(laterInput);
        markInvalid(soonerInput);
        return false;
    }
    return true;

}

function validateRequired(form, validateHidden = false) {
    console.log(form, validateHidden);
    let isValid = true;
    let inputs = $(form).find("input, textarea, select");

    inputs.each((index, element) => {
        element = $(element);
        console.log(element, element.val())

        if ((element.is(":visible") || validateHidden) && element.is(":required") && element.val() === "") {
            markInvalid(element);
            isValid = false;
        } else {
            markValid(element);
        }

    });
    console.log("vysledek validateRequired");
    console.log(isValid);
    return isValid;
}

function markValid(input) {
    input.addClass("is-valid");
    setTimeout(() => input.removeClass("is-valid"), 2000)
}

function markInvalid(input) {
    input.addClass("is-invalid");
    setTimeout(() => input.removeClass("is-invalid"), 2000)
}