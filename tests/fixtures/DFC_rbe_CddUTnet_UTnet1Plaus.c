/* DFC_rbe_CddUTnet_UTnet1Plaus - Plausibility check for UTnet1
 * This DFC monitors the plausibility of the UTnet1 signal.
 */

#include "CddUTnet.h"
#include "DFC_rbe_CddUTnet.h"
#include "Dem.h"

#define DFC_rbe_CddUTnet_UTnet1Plaus_THRESHOLD  (0x10U)
#define DFC_rbe_CddUTnet_UTnet1Plaus_DEBOUNCE   (200U)

typedef enum {
    DFC_rbe_CddUTnet_UTnet1Plaus_NotTested = 0,
    DFC_rbe_CddUTnet_UTnet1Plaus_Passed    = 1,
    DFC_rbe_CddUTnet_UTnet1Plaus_Failed    = 2,
} DFC_rbe_CddUTnet_UTnet1Plaus_StatusType;

/* Run the DFC_rbe_CddUTnet_UTnet1Plaus plausibility check */
void DFC_rbe_CddUTnet_UTnet1Plaus_Run(void) {
    uint8 signal = CddUTnet_GetUTnet1Signal();
    if (signal > DFC_rbe_CddUTnet_UTnet1Plaus_THRESHOLD) {
        Dem_ReportErrorStatus(DFC_rbe_CddUTnet_UTnet1Plaus_ID, DEM_EVENT_STATUS_FAILED);
    } else {
        Dem_ReportErrorStatus(DFC_rbe_CddUTnet_UTnet1Plaus_ID, DEM_EVENT_STATUS_PASSED);
    }
}
