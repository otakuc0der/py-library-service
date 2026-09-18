from datetime import date


def get_borrowing_date_errors(
    borrow_date: date | None,
    expected_return_date: date | None,
    actual_return_date: date | None = None,
) -> dict[str, str]:
    errors = {}

    if (
        borrow_date is not None
        and expected_return_date is not None
        and expected_return_date < borrow_date
    ):
        errors["expected_return_date"] = (
            "Expected return date cannot be earlier "
            "than borrow date."
        )

    if (
        borrow_date is not None
        and actual_return_date is not None
        and actual_return_date < borrow_date
    ):
        errors["actual_return_date"] = (
            "Actual return date cannot be earlier "
            "than borrow date."
        )

    return errors
