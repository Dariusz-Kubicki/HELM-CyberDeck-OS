/*
    SPDX-FileCopyrightText: 2016 David Edmundson <davidedmundson@kde.org>

    SPDX-License-Identifier: LGPL-2.0-or-later
*/

import QtQuick

import QtQuick.Layouts
import QtQuick.Controls as QQC2

import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.extras as PlasmaExtras
import org.kde.kirigami as Kirigami
import org.kde.kscreenlocker as ScreenLocker

import org.kde.breeze.components

SessionManagementScreen {
    id: sessionManager

    readonly property alias mainPasswordBox: passwordBox
    property bool lockScreenUiVisible: false
    property alias showPassword: passwordBox.showPassword

    //the y position that should be ensured visible when the on screen keyboard is visible
    property int visibleBoundary: mapFromItem(loginButton, 0, 0).y
    onHeightChanged: visibleBoundary = mapFromItem(loginButton, 0, 0).y + loginButton.height + Kirigami.Units.smallSpacing
    /*
     * Login has been requested with the following username and password
     * If username field is visible, it will be taken from that, otherwise from the "name" property of the currentIndex
     */
    signal passwordResult(string password)

    onUserSelected: {
        const nextControl = (passwordBox.visible ? passwordBox : loginButton);
        // Don't startLogin() here, because the signal is connected to the
        // Escape key as well, for which it wouldn't make sense to trigger
        // login. Using TabFocusReason, so that the loginButton gets the
        // visual highlight.
        nextControl.forceActiveFocus(Qt.TabFocusReason);
    }

    function startLogin() {
        const password = passwordBox.text

        // This is partly because it looks nicer, but more importantly it
        // works round a Qt bug that can trigger if the app is closed with a
        // TextField focused.
        //
        // See https://bugreports.qt.io/browse/QTBUG-55460
        loginButton.forceActiveFocus();
        passwordResult(password);
    }

    // HELM-STYLE: security-lock-controls-v2
    ColumnLayout {
        Layout.fillWidth: true
        spacing: 10

        Text {
            Layout.fillWidth: true

            text: "LOCAL CREDENTIAL CHANNEL"
            color: "#42E8FF"

            horizontalAlignment: Text.AlignHCenter

            font.family: "Hack"
            font.pixelSize: 10
            font.bold: true
            font.letterSpacing: 0.65
        }

        QQC2.TextField {
            id: passwordBox

            property bool showPassword: false

            Layout.fillWidth: true
            Layout.preferredHeight: 45

            text: PasswordSync.password
            echoMode: showPassword ? TextInput.Normal : TextInput.Password
            passwordCharacter: "●"

            placeholderText: "PASSWORD CREDENTIAL"
            placeholderTextColor: "#587982"

            color: "#E5FBFF"
            selectionColor: "#42E8FF"
            selectedTextColor: "#02070B"

            font.family: "Hack"
            font.pixelSize: 12

            leftPadding: 16
            rightPadding: 16

            focus: true
            enabled: !authenticator.graceLocked
            selectByMouse: true
            cursorVisible: visible

            background: Rectangle {
                color: "#FF071116"

                border.color:
                    passwordBox.activeFocus
                    ? "#42E8FF"
                    : "#497C8990"

                border.width:
                    passwordBox.activeFocus
                    ? 2
                    : 1

                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom

                    width: 3
                    color: "#42E8FF"
                }
            }

            onAccepted: {
                if (sessionManager.lockScreenUiVisible) {
                    sessionManager.startLogin();
                }
            }

            Keys.onPressed: event => {
                if (event.key === Qt.Key_Left && !text) {
                    sessionManager.userList.decrementCurrentIndex();
                    event.accepted = true
                }
                if (event.key === Qt.Key_Right && !text) {
                    sessionManager.userList.incrementCurrentIndex();
                    event.accepted = true
                }
            }

            Connections {
                target: root

                function onClearPassword() {
                    passwordBox.forceActiveFocus()
                    passwordBox.text = "";
                    passwordBox.text = Qt.binding(() => PasswordSync.password);
                }

                function onNotificationRepeated() {
                    sessionManager.playHighlightAnimation();
                }
            }
        }

        Binding {
            target: PasswordSync
            property: "password"
            value: passwordBox.text
        }

        QQC2.Button {
            id: loginButton

            Accessible.name: i18ndc("plasma_shell_org.kde.plasma.desktop", "@action:button accessible only", "Unlock")

            Layout.fillWidth: true
            Layout.preferredHeight: 47

            hoverEnabled: true

            onClicked: sessionManager.startLogin()
            Keys.onEnterPressed: clicked()
            Keys.onReturnPressed: clicked()

            contentItem: Text {
                text: "AUTHENTICATE"

                color:
                    loginButton.hovered
                    ? "#02070B"
                    : "#42E8FF"

                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter

                font.family: "Hack"
                font.pixelSize: 12
                font.bold: true
                font.letterSpacing: 1
            }

            background: Rectangle {
                color:
                    loginButton.hovered
                    ? "#42E8FF"
                    : "#0C1920"

                border.color: "#42E8FF"
                border.width: 1

                Behavior on color {
                    ColorAnimation {
                        duration: 130
                    }
                }
            }
        }
    }

    component FailableLabel : PlasmaComponents3.Label {
        id: _failableLabel
        required property int kind
        required property string label

        visible: authenticator.authenticatorTypes & kind
        text: label
        textFormat: Text.PlainText
        horizontalAlignment: Text.AlignHCenter
        Layout.fillWidth: true

        RejectPasswordAnimation {
            id: _rejectAnimation
            target: _failableLabel
            onFinished: _timer.restart()
        }

        Connections {
            target: authenticator
            function onNoninteractiveError(kind, authenticator) {
                if (kind & _failableLabel.kind) {
                    _failableLabel.text = Qt.binding(() => authenticator.errorMessage)
                    _rejectAnimation.start()
                }
            }
        }
        Timer {
            id: _timer
            interval: Kirigami.Units.humanMoment
            onTriggered: {
                _failableLabel.text = Qt.binding(() => _failableLabel.label)
            }
        }
    }

    FailableLabel {
        kind: ScreenLocker.Authenticator.Fingerprint
        label: i18ndc("plasma_shell_org.kde.plasma.desktop", "@info:usagetip", "(or scan your fingerprint on the reader)")
    }
    FailableLabel {
        kind: ScreenLocker.Authenticator.Smartcard
        label: i18ndc("plasma_shell_org.kde.plasma.desktop", "@info:usagetip", "(or scan your smartcard)")
    }
}
