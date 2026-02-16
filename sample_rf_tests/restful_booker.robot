*** Settings ***
Library    RequestsLibrary
Library    DateTime
Library    Collections
Library    OperatingSystem
Suite Setup    Authenticate as Admin

*** Variables ***
${RESPONSE_FILE}  newBooking.json

*** Test Cases ***
Get Bookings from Restful Booker
    ${now}=    Get Current Date
    ${start_date}=      Subtract Time From Date   ${now}     3 days    result_format=%Y-%m-%d
    ${response}    GET    https://restful-booker.herokuapp.com/booking    params=checkin=${start_date}
    Status Should Be    200
    Log List    ${response.json()}
    FOR  ${booking}  IN  @{response.json()}
        ${response}    GET    https://restful-booker.herokuapp.com/booking/${booking}[bookingid]
        TRY
            Log    ${response.json()}
        EXCEPT
            Log    Cannot retrieve JSON due to invalid data
        END
    END

Create a Booking at Restful Booker
    ${booking_dates}    Create Dictionary    checkin=2025-12-31    checkout=2026-01-01
    ${body}    Create Dictionary    firstname=Hans    lastname=Gruber    totalprice=200    depositpaid=false    bookingdates=${booking_dates}
    ${response}    POST    url=https://restful-booker.herokuapp.com/booking    json=${body}
    ${id}    Set Variable    ${response.json()}[bookingid]
    Set Suite Variable    ${id}
    ${response}    GET    https://restful-booker.herokuapp.com/booking/${id}
    Log    ${response.json()}
    ${json_response}=   Convert To String   ${response.json()}
    Create File   ${RESPONSE_FILE}   ${json_response}
    Should Be Equal    ${response.json()}[lastname]    Gruber
    Should Be Equal    ${response.json()}[firstname]    Hans
    Should Be Equal As Numbers    ${response.json()}[totalprice]    200
    Dictionary Should Contain Value     ${response.json()}    Gruber

Delete Booking
    ${header}    Create Dictionary    Cookie=token\=${token}
    ${response}    DELETE    url=https://restful-booker.herokuapp.com/booking/${id}    headers=${header}   
    Status Should Be    201    ${response}
    
A skipped test
    Skip

*** Keywords ***
Authenticate as Admin
    ${body}    Create Dictionary    username=admin    password=password123
    ${response}    POST    url=https://restful-booker.herokuapp.com/auth    json=${body}
    Log    ${response.json()}
    ${token}    Set Variable    ${response.json()}[token]
    Log    ${token}
    Set Suite Variable    ${token}