class LedgerError(Exception):
    pass


class InvalidJournalLineError(LedgerError):
    pass


class JournalEntryNotBalancedError(LedgerError):
    pass


class JournalEntryRequiresAtLeastTwoLinesError(LedgerError):
    pass


class JournalEntryAmountMustBePositiveError(LedgerError):
    pass


class LedgerAccountNotFoundError(LedgerError):
    pass


class LedgerAccountInactiveError(LedgerError):
    pass
