# CryptoCurrencies 2022 ex6 tests

## Usage
 - navigate to your `tests` directory within the ex6 brownie project.  
 - clone this project into a subdirectory, e.g ```git clone <repository_link> extra_tests```
 - run tests with `brownie test` as usual.

## Test Scenarios implemented

 - Alice tries to transfer money without reducing her own balance.
 - Alice tries to transfer money with a bad signature.
 - Alice tries to transfer money with a bad serial.
 - Try to close a channel with different than original balance.
 - Alice tries to ack a valid but wrong amount.
 - Alice tries to ack an invalid amount.
 - Alice tries to notify of a channel with a low appeal period.
 - Alice tries to notify bob of a channel that bob established.
 - Alice tries to close a channel with a modified-serial state.
 
Keep in mind that I made an effort to make these tests independant of individual implementations, but I may have missed something.  

Please feel free to add scenarios and share them (best to use pull request).