/*
    SPDX-FileCopyrightText: 2014 Aleix Pol Gonzalez <aleixpol@blue-systems.com>

    SPDX-License-Identifier: GPL-2.0-or-later
*/

import QtQuick

Item {
    id: root
    property bool debug: false
    property string notification
    signal clearPassword()
    signal notificationRepeated()

    // These are magical properties that kscreenlocker looks for
    property bool viewVisible: false

    LayoutMirroring.enabled: Application.layoutDirection === Qt.RightToLeft
    LayoutMirroring.childrenInherit: true

    implicitWidth: 800
    implicitHeight: 600

    LockScreenUi {
        anchors.fill: parent
    }


    /*
     * HELM CYBERDECK SECURITY LOCK
     * Visual-only overlay. Authentication remains handled
     * by the original Plasma lock screen implementation.
     */
    Rectangle {
        id: helmSecurityOverlay

        z: 10000

        anchors.left: parent.left
        anchors.top: parent.top
        anchors.leftMargin: 38
        anchors.topMargin: 38

        width: Math.min(520, parent.width * 0.42)
        height: 138

        color: "#EE02070B"
        border.color: "#42E8FF"
        border.width: 1
        radius: 0

        Rectangle {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom

            width: 7
            color: "#42E8FF"
        }

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top

            anchors.leftMargin: 20
            anchors.rightMargin: 12
            anchors.topMargin: 66

            height: 1
            color: "#174B5A"
        }

        Column {
            anchors.fill: parent
            anchors.leftMargin: 29
            anchors.rightMargin: 18
            anchors.topMargin: 15
            anchors.bottomMargin: 12

            spacing: 4

            Text {
                text: "◈  H  E  L  M"

                color: "#8CF5FF"

                font.family: "Hack"
                font.pixelSize: 20
                font.bold: true
            }

            Text {
                text: "SECURITY LOCK  //  CYBERDECK OS 1.0"

                color: "#D9F3FF"

                font.family: "Hack"
                font.pixelSize: 13
                font.bold: true
            }

            Item {
                width: 1
                height: 8
            }

            Text {
                text: "● SESSION SEALED"

                color: "#58F6D0"

                font.family: "Hack"
                font.pixelSize: 12
                font.bold: true
            }

            Text {
                text: "OPERATOR DARIUSZ  //  AUTHENTICATION REQUIRED"

                color: "#6F9DA8"

                font.family: "Hack"
                font.pixelSize: 11
            }
        }
    }

}
