#include "arch.h"
#include <libloaderapi.h>
#include <windef.h>
#include <processthreadsapi.h>
#include <detours/detours.h>

#include "constants.hpp"
#include "tapsite.hpp"
#include "taskbarappearanceservice.hpp"

BOOL WINAPI DllMain(HINSTANCE, DWORD fdwReason, LPVOID) noexcept
{
	switch (fdwReason)
	{
	case DLL_PROCESS_ATTACH:
	{
		// Are we in Explorer?
		void* payload = DetourFindPayloadEx(EXPLORER_PAYLOAD, nullptr);
		if (payload)
		{
			// This DLL is only held in Explorer by TranslucentTB's window hook until InitializeXamlDiagnosticsEx
			// pins it. If TranslucentTB stops waiting (ready timeout, retry or exit) while the install thread
			// is still retrying, the hook goes away and Explorer could unload this code under that thread.
			// Give the thread its own reference, released with FreeLibraryAndExitThread when it is done,
			// so a failed install still unloads the DLL afterwards.
			HMODULE self = nullptr;
			if (!GetModuleHandleEx(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS, reinterpret_cast<LPCWSTR>(&DllMain), &self)) [[unlikely]]
			{
				self = nullptr;
			}

			// Install the thing
			wil::unique_handle handle(CreateThread(nullptr, 0, TAPSite::Install, self, 0, nullptr));
			if (!handle)
			{
				return false;
			}
		}
		break;
	}

	case DLL_PROCESS_DETACH:
		TaskbarAppearanceService::UninstallProxyStub();
		break;
	}

	return true;
}
